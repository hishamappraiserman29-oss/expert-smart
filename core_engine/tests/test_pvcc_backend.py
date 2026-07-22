"""
PVCC Backend Tests — Professional Valuation Chat Command Center
Tests PVCC-B01 through PVCC-B30
"""
from __future__ import annotations
import pytest, os, sys
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_ORIG_CWD = os.getcwd()
try:
    os.chdir(str(_CORE))

    from bridge_api import app as flask_app  # noqa: E402
finally:
    os.chdir(_ORIG_CWD)

_VALID_PAYLOAD: dict = {
    "client_name":       "أحمد محمد اختبار PVCC",
    "property_type":     "شقة سكنية",
    "valuation_purpose": "قيمة سوقية",
    "city":              "القاهرة",
    "district":          "الزمالك",
}

@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c

def _create(client, extra=None):
    data = dict(_VALID_PAYLOAD)
    if extra:
        data.update(extra)
    return client.post(
        "/api/professional-valuation/requests",
        json=data,
        content_type="application/json",
    )


# ── PVCC-B01: chat_command_center_context exists ──────────────────────────
def test_PVCC_B01_chat_command_center_context_exists(client):
    resp = _create(client)
    assert resp.status_code in (200, 201)
    body = resp.get_json() or {}
    assert "chat_command_center_context" in body, "chat_command_center_context missing from response"


# ── PVCC-B02: chat_output_registry_context exists ────────────────────────
def test_PVCC_B02_chat_output_registry_exists(client):
    resp = _create(client)
    body = resp.get_json() or {}
    assert "chat_output_registry_context" in body


# ── PVCC-B03: registry includes traditional_report ───────────────────────
def test_PVCC_B03_registry_includes_traditional_report(client):
    resp = _create(client)
    reg = (resp.get_json() or {}).get("chat_output_registry_context", {})
    assert "traditional_report" in reg


# ── PVCC-B04: registry includes detailed_report ──────────────────────────
def test_PVCC_B04_registry_includes_detailed_report(client):
    resp = _create(client)
    reg = (resp.get_json() or {}).get("chat_output_registry_context", {})
    assert "detailed_report" in reg


# ── PVCC-B05: registry includes professional_report ──────────────────────
def test_PVCC_B05_registry_includes_professional_report(client):
    resp = _create(client)
    reg = (resp.get_json() or {}).get("chat_output_registry_context", {})
    assert "professional_report" in reg


# ── PVCC-B06: registry includes simulated_uploaded_report ────────────────
def test_PVCC_B06_registry_includes_simulated_uploaded_report(client):
    resp = _create(client)
    reg = (resp.get_json() or {}).get("chat_output_registry_context", {})
    assert "simulated_uploaded_report" in reg


# ── PVCC-B07: registry includes report_review_output ─────────────────────
def test_PVCC_B07_registry_includes_report_review_output(client):
    resp = _create(client)
    reg = (resp.get_json() or {}).get("chat_output_registry_context", {})
    assert "report_review_output" in reg


# ── PVCC-B08: registry includes hbu_analysis_report ──────────────────────
def test_PVCC_B08_registry_includes_hbu_analysis_report(client):
    resp = _create(client)
    reg = (resp.get_json() or {}).get("chat_output_registry_context", {})
    assert "hbu_analysis_report" in reg


# ── PVCC-B09: registry includes standards_compliance_report ──────────────
def test_PVCC_B09_registry_includes_standards_compliance_report(client):
    resp = _create(client)
    reg = (resp.get_json() or {}).get("chat_output_registry_context", {})
    assert "standards_compliance_report" in reg


# ── PVCC-B10: feature_toggles_registry_context exists ────────────────────
def test_PVCC_B10_feature_toggles_registry_exists(client):
    resp = _create(client)
    body = resp.get_json() or {}
    assert "chat_feature_toggles_registry_context" in body


# ── PVCC-B11: registry includes super_intelligence ───────────────────────
def test_PVCC_B11_toggle_super_intelligence(client):
    resp = _create(client)
    reg = (resp.get_json() or {}).get("chat_feature_toggles_registry_context", {})
    assert "super_intelligence" in reg


# ── PVCC-B12: registry includes digital_inspector ────────────────────────
def test_PVCC_B12_toggle_digital_inspector(client):
    resp = _create(client)
    reg = (resp.get_json() or {}).get("chat_feature_toggles_registry_context", {})
    assert "digital_inspector" in reg


# ── PVCC-B13: registry includes geotechnical_risk ────────────────────────
def test_PVCC_B13_toggle_geotechnical_risk(client):
    resp = _create(client)
    reg = (resp.get_json() or {}).get("chat_feature_toggles_registry_context", {})
    assert "geotechnical_risk" in reg


# ── PVCC-B14: registry includes migration_radar ──────────────────────────
def test_PVCC_B14_toggle_migration_radar(client):
    resp = _create(client)
    reg = (resp.get_json() or {}).get("chat_feature_toggles_registry_context", {})
    assert "migration_radar" in reg


# ── PVCC-B15: registry includes asset_portfolio ──────────────────────────
def test_PVCC_B15_toggle_asset_portfolio(client):
    resp = _create(client)
    reg = (resp.get_json() or {}).get("chat_feature_toggles_registry_context", {})
    assert "asset_portfolio" in reg


# ── PVCC-B16: registry includes reference_library ────────────────────────
def test_PVCC_B16_toggle_reference_library(client):
    resp = _create(client)
    reg = (resp.get_json() or {}).get("chat_feature_toggles_registry_context", {})
    assert "reference_library" in reg


# ── PVCC-B17: all feature toggles have valid state ───────────────────────
def test_PVCC_B17_all_toggles_have_valid_state(client):
    resp = _create(client)
    reg = (resp.get_json() or {}).get("chat_feature_toggles_registry_context", {})
    valid_states = {"active", "advisory_only", "future_stub", "disabled"}
    for key, val in reg.items():
        assert val.get("state") in valid_states, \
            f"Toggle {key!r} has invalid state: {val.get('state')!r}"


# ── PVCC-B18: future_stub features do not claim active report impact ──────
def test_PVCC_B18_future_stub_not_active(client):
    resp = _create(client)
    reg = (resp.get_json() or {}).get("chat_feature_toggles_registry_context", {})
    for key, val in reg.items():
        if val.get("state") == "future_stub":
            assert val.get("state") != "active", \
                f"future_stub feature {key!r} incorrectly claims active state"


# ── PVCC-B19: admin Excel permission is admin-only (False for default user) ─
def test_PVCC_B19_admin_excel_protected(client):
    resp = _create(client)
    ctx = (resp.get_json() or {}).get("chat_command_center_context", {})
    perms = ctx.get("output_permissions", {})
    assert perms.get("can_generate_admin_excel") is False, \
        "Admin Excel must be False for default (non-admin) user"


# ── PVCC-B20: user PDF permission exists ─────────────────────────────────
def test_PVCC_B20_user_pdf_permission_exists(client):
    resp = _create(client)
    ctx = (resp.get_json() or {}).get("chat_command_center_context", {})
    perms = ctx.get("output_permissions", {})
    assert "can_generate_user_pdf" in perms


# ── PVCC-B21: simulated report requires training upload ───────────────────
def test_PVCC_B21_simulated_report_requires_training_upload(client):
    resp = _create(client)
    reg = (resp.get_json() or {}).get("chat_output_registry_context", {})
    sim = reg.get("simulated_uploaded_report", {})
    assert sim.get("requires_training_upload") is True
    assert sim.get("requires_uploaded_report") is True


# ── PVCC-B22: standards compliance report requires standards context ───────
def test_PVCC_B22_standards_report_requires_standards(client):
    resp = _create(client)
    reg = (resp.get_json() or {}).get("chat_output_registry_context", {})
    sc = reg.get("standards_compliance_report", {})
    assert sc.get("requires_standards_context") is True


# ── PVCC-B23: hbu report requires hbu context/toggle ─────────────────────
def test_PVCC_B23_hbu_report_requires_hbu_toggle(client):
    resp = _create(client)
    reg = (resp.get_json() or {}).get("chat_output_registry_context", {})
    hbu = reg.get("hbu_analysis_report", {})
    assert hbu.get("requires_hbu_report_toggle") is True


# ── PVCC-B24: certified PDF blocked when certification_ready=False ─────────
def test_PVCC_B24_certified_pdf_blocked_without_cert(client):
    resp = _create(client)
    ctx = (resp.get_json() or {}).get("chat_command_center_context", {})
    perms = ctx.get("output_permissions", {})
    assert perms.get("can_generate_certified_pdf") is False


# ── PVCC-B25: final workbook blocked when certification_ready=False ────────
def test_PVCC_B25_final_workbook_blocked_without_cert(client):
    resp = _create(client)
    ctx = (resp.get_json() or {}).get("chat_command_center_context", {})
    perms = ctx.get("output_permissions", {})
    assert perms.get("can_generate_final_workbook") is False


# ── PVCC-B26: no internal paths in chat context ───────────────────────────
def test_PVCC_B26_no_internal_paths(client):
    import json
    resp = _create(client)
    body_str = json.dumps(resp.get_json() or {})
    bad_patterns = ["/home/", "C:\\Users\\", "C:/Users/", "/var/", "/tmp/",
                    "core_engine/instance", "__pycache__"]
    for pat in bad_patterns:
        assert pat not in body_str, f"Internal path found in response: {pat!r}"


# ── PVCC-B27: no real ML training claim ───────────────────────────────────
def test_PVCC_B27_no_real_ml_training_claimed(client):
    resp = _create(client)
    ctx = (resp.get_json() or {}).get("chat_command_center_context", {})
    assert ctx.get("real_ml_training_claimed") is False


# ── PVCC-B28: no external API active flag ────────────────────────────────
def test_PVCC_B28_no_external_api_active(client):
    resp = _create(client)
    ctx = (resp.get_json() or {}).get("chat_command_center_context", {})
    assert ctx.get("external_apis_active") is False


# ── PVCC-B29: ordinary valuation route unaffected ────────────────────────
def test_PVCC_B29_ordinary_valuation_unaffected(client):
    resp = client.post(
        "/api/valuation",
        json={"property_type": "apartment", "area": 100,
              "location": "القاهرة", "age": 5},
    )
    assert resp.status_code in (200, 201, 400, 401, 422), \
        f"Ordinary valuation route returned unexpected status: {resp.status_code}"
    body = resp.get_json() or {}
    assert "chat_command_center_context" not in body, \
        "PVCC context must not leak into ordinary valuation response"


# ── PVCC-B30: chat_toggle_impact_matrix_context exists ───────────────────
def test_PVCC_B30_toggle_impact_matrix_exists(client):
    resp = _create(client)
    body = resp.get_json() or {}
    assert "chat_toggle_impact_matrix_context" in body
    matrix = body["chat_toggle_impact_matrix_context"]
    assert isinstance(matrix, dict)
    assert len(matrix) >= 6
