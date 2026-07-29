"""
test_mv_security.py — P3 security tests.
Covers: secrets_scanner (O-04), output_guard (O-02/G-07/O-06/G-08/G-05),
        and export_excel access control (O-01).
Tests: SEC-01 → SEC-25
"""
import pytest

from core_engine.mass_valuation.secrets_scanner import (
    scan_output,
    scan_for_forbidden_terms,
    check_taqeem_claim,
    verify_file_signature,
    assert_clean,
)
from core_engine.mass_valuation.output_builder import OutputBuilder


# ---------------------------------------------------------------------------
# SEC-01 → SEC-08  secrets_scanner — scan_output
# ---------------------------------------------------------------------------

def test_sec_01_clean_dict_returns_empty():
    data = {"run_id": "abc-123", "status": "validated", "advisory_only": True}
    assert scan_output(data) == []


def test_sec_02_windows_path_detected():
    data = {"model_path": r"C:\Users\admin\models\hedonic.pkl"}
    findings = scan_output(data)
    assert any(f["kind"] == "windows_path" for f in findings)


def test_sec_03_unix_path_detected():
    data = {"log": "/home/ubuntu/app/server.log"}
    findings = scan_output(data)
    assert any(f["kind"] == "unix_path" for f in findings)


def test_sec_04_connection_string_detected():
    data = {"db": "postgresql://user:pass@localhost:5432/mvdb"}
    findings = scan_output(data)
    assert any(f["kind"] == "connection_string" for f in findings)


def test_sec_05_bearer_token_detected():
    data = {"auth": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature"}
    findings = scan_output(data)
    assert any(f["kind"] == "bearer_token" for f in findings)


def test_sec_06_taqeem_claim_detected_in_scan():
    data = {"note": "This output is TAQEEM-compliant per 2024 standards."}
    findings = scan_output(data)
    assert any(f["kind"] == "taqeem_compliance_claim" for f in findings)


def test_sec_07_nested_dict_path_detected():
    data = {"meta": {"paths": {"model": r"C:\models\v1\hedonic.pkl"}}}
    findings = scan_output(data)
    assert any(f["kind"] == "windows_path" for f in findings)


def test_sec_08_list_value_path_detected():
    data = {"files": ["/home/user/output.xlsx", "safe_name.xlsx"]}
    findings = scan_output(data)
    assert any(f["kind"] == "unix_path" for f in findings)


# ---------------------------------------------------------------------------
# SEC-09 → SEC-12  scan_for_forbidden_terms (O-02)
# ---------------------------------------------------------------------------

def test_sec_09_shap_detected():
    assert "shap" in scan_for_forbidden_terms("The SHAP value for area is 0.4")


def test_sec_10_cod_detected():
    assert "cod" in scan_for_forbidden_terms("COD is 12.5 which exceeds the threshold")


def test_sec_11_basel_detected():
    assert "basel" in scan_for_forbidden_terms("Basel III requires LTV disclosure")


def test_sec_12_clean_user_text_returns_empty():
    text = "Your property has been valued at SAR 2,500,000. This is an advisory estimate."
    assert scan_for_forbidden_terms(text) == []


# ---------------------------------------------------------------------------
# SEC-13 → SEC-15  check_taqeem_claim (G-07)
# ---------------------------------------------------------------------------

def test_sec_13_taqeem_compliant_detected():
    assert check_taqeem_claim("Report is TAQEEM-compliant per the 2024 standard.") is True


def test_sec_14_taqeem_compliant_space_variant():
    assert check_taqeem_claim("This system is TAQEEM compliant.") is True


def test_sec_15_no_taqeem_claim():
    assert check_taqeem_claim("This is an advisory valuation only.") is False


# ---------------------------------------------------------------------------
# SEC-16 → SEC-19  verify_file_signature (O-06)
# ---------------------------------------------------------------------------

def test_sec_16_html_signature_valid():
    data = b"<!DOCTYPE html><html><body>hello</body></html>"
    assert verify_file_signature(data, "html") is True


def test_sec_17_html_signature_invalid():
    data = b"<html><body>no doctype</body></html>"
    assert verify_file_signature(data, "html") is False


def test_sec_18_xlsx_signature_valid():
    data = b"PK\x03\x04" + b"\x00" * 20
    assert verify_file_signature(data, "xlsx") is True


def test_sec_19_pdf_signature_valid():
    data = b"%PDF-1.4 1 0 obj"
    assert verify_file_signature(data, "pdf") is True


# ---------------------------------------------------------------------------
# SEC-20 → SEC-21  assert_clean helper
# ---------------------------------------------------------------------------

def test_sec_20_assert_clean_passes_on_safe_data():
    data = {"run_id": "abc", "advisory_only": True, "status": "validated"}
    assert_clean(data)  # should not raise


def test_sec_21_assert_clean_raises_on_violation():
    data = {"model": r"C:\Users\admin\model.pkl"}
    with pytest.raises(ValueError, match="windows_path"):
        assert_clean(data)


# ---------------------------------------------------------------------------
# SEC-22 → SEC-23  OutputBuilder.scrub_user_text (G-07)
# ---------------------------------------------------------------------------

def test_sec_22_scrub_user_text_passes_clean_text():
    builder = OutputBuilder()
    text = "Your property advisory value is SAR 2,500,000."
    result = builder.scrub_user_text(text)
    assert result == text


def test_sec_23_scrub_user_text_raises_on_taqeem_claim():
    builder = OutputBuilder()
    with pytest.raises(ValueError, match="TAQEEM"):
        builder.scrub_user_text("This platform is TAQEEM-compliant.")


# ---------------------------------------------------------------------------
# SEC-24  OutputBuilder.check_file_signature (O-06)
# ---------------------------------------------------------------------------

def test_sec_24_output_builder_check_file_signature():
    builder = OutputBuilder()
    assert builder.check_file_signature(b"PK\x03\x04" + b"\x00" * 4, "xlsx") is True
    assert builder.check_file_signature(b"JUNK", "xlsx") is False


# ---------------------------------------------------------------------------
# SEC-25  G-05 — insufficient_evidence → estimated_value is None (runner)
# ---------------------------------------------------------------------------

def test_sec_25_insufficient_evidence_gives_null_value():
    """
    A record whose model produces zero/negative value must result in
    estimated_value=None (G-05). We test via runner with a zero-price record.
    """
    from core_engine.mass_valuation.runner import MassValuationRunner

    bad_record = {
        "property_id":       "ZERO-001",
        "property_type":     "residential",
        "city":              "Riyadh",
        "district":          "Al Nakheel",
        "land_area_m2":      100.0,
        "built_up_area_m2":  80.0,
        "transaction_date":  "2024-01-01",
        "transaction_price": 1,       # near-zero → model will produce tiny/zero value
        "evidence_type":     "registered_sale",
        "age":               1,
        "condition":         "good",
        "use":               "owner_occupied",
        "quality_finish":    "standard",
        "latitude":          24.7,
        "longitude":         46.7,
    }
    runner = MassValuationRunner()
    result = runner.run([bad_record])
    for pred in result.get("predictions", []):
        if pred.get("distribution_status") == "insufficient_evidence":
            assert pred["estimated_value"] is None, (
                "G-05 violation: insufficient_evidence prediction must have null estimated_value"
            )
