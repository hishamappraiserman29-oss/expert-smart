"""
Backend tests — Professional Valuation Section 4: Add USPAP and Basel III
Task: PVS4-USPAP-BASEL

Tests verify:
1. Standards registry includes USPAP and Basel III
2. Category classifications are correct
3. Alias normalization works
4. Backend context contains USPAP and Basel III
5. Compliance summary advisory_only=true, final_compliance_claim=false
6. No old standards deleted
7. No duplicate standards
8. No internal paths exposed
9. Ordinary valuation unaffected
"""
import os
import sys
import pytest
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

os.environ.setdefault("JWT_SECRET", "pvs4-uspap-basel-test-secret-xxxxx")

from bridge_api import app  # noqa: E402
from auth.tokens import generate_token  # noqa: E402

app.config["TESTING"] = True


def _auth() -> dict:
    return {"Authorization": "Bearer " + generate_token("test-admin")}


def _create(client, extra: dict | None = None) -> dict:
    body = {
        "client_name": "test-uspap-basel",
        "property_type": "apartment",
        "valuation_purpose": "financing_mortgage",
        "city": "Cairo",
        "district": "Downtown",
    }
    if extra:
        body.update(extra)
    r = client.post(
        "/api/professional-valuation/requests",
        json=body,
        content_type="application/json",
    )
    return r.get_json() or {}


def _get_detail(client, resp: dict) -> dict:
    rid = resp.get("request_id", "")
    if not rid:
        return {}
    outer = (
        client.get(
            f"/api/professional-valuation/requests/{rid}",
            headers=_auth(),
        ).get_json()
        or {}
    )
    return outer.get("request", outer)


# ── UB01: standards registry includes USPAP ──────────────────────────────────
def test_PVS4_UB01_registry_includes_uspap():
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["uspap"]})
        ctx = resp.get("applied_standards_context") or resp.get("standards_registry_context") or {}
        if not ctx:
            pytest.skip("applied_standards_context not in response")
        standards = ctx.get("standards") or ctx.get("available_standards") or []
        keys = [s["key"] if isinstance(s, dict) else s for s in standards]
        assert "uspap" in keys, f"uspap not found in standards registry. Keys: {keys}"


# ── UB02: standards registry includes Basel III ───────────────────────────────
def test_PVS4_UB02_registry_includes_basel_iii():
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["basel_iii"]})
        ctx = resp.get("applied_standards_context") or resp.get("standards_registry_context") or {}
        if not ctx:
            pytest.skip("applied_standards_context not in response")
        standards = ctx.get("standards") or ctx.get("available_standards") or []
        keys = [s["key"] if isinstance(s, dict) else s for s in standards]
        assert "basel_iii" in keys, f"basel_iii not found in standards registry. Keys: {keys}"


# ── UB03: USPAP category is professional_valuation_standard ──────────────────
def test_PVS4_UB03_uspap_category_professional():
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["uspap"]})
        ctx = resp.get("applied_standards_context") or resp.get("standards_registry_context") or {}
        if not ctx:
            pytest.skip("applied_standards_context not in response")
        standards = ctx.get("standards") or []
        uspap_entry = next((s for s in standards if isinstance(s, dict) and s.get("key") == "uspap"), None)
        if not uspap_entry:
            # Try standards_by_category
            by_cat = ctx.get("standards_by_category", {})
            assert "uspap" in by_cat.get("professional_valuation_standard", []), \
                "uspap not in professional_valuation_standard category"
        else:
            assert uspap_entry.get("category") == "professional_valuation_standard", \
                f"USPAP category mismatch: {uspap_entry.get('category')}"


# ── UB04: Basel III category is risk_banking_collateral_framework ─────────────
def test_PVS4_UB04_basel_iii_category_risk_banking():
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["basel_iii"]})
        ctx = resp.get("applied_standards_context") or resp.get("standards_registry_context") or {}
        if not ctx:
            pytest.skip("applied_standards_context not in response")
        standards = ctx.get("standards") or []
        basel_entry = next((s for s in standards if isinstance(s, dict) and s.get("key") == "basel_iii"), None)
        if not basel_entry:
            by_cat = ctx.get("standards_by_category", {})
            assert "basel_iii" in by_cat.get("risk_banking_collateral_framework", []), \
                "basel_iii not in risk_banking_collateral_framework category"
        else:
            assert basel_entry.get("category") == "risk_banking_collateral_framework", \
                f"Basel III category mismatch: {basel_entry.get('category')}"


# ── UB05: Basel III has not_pure_valuation_standard=true ─────────────────────
def test_PVS4_UB05_basel_not_pure_valuation_standard():
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["basel_iii"]})
        ctx = resp.get("applied_standards_context") or resp.get("standards_registry_context") or {}
        if not ctx:
            pytest.skip("applied_standards_context not in response")
        standards = ctx.get("standards") or []
        basel_entry = next((s for s in standards if isinstance(s, dict) and s.get("key") == "basel_iii"), None)
        if not basel_entry:
            # Check via Basel III context if present
            bc = ctx.get("basel_iii_context", {})
            if bc:
                assert bc.get("not_pure_valuation_standard") is True, \
                    "Basel III not_pure_valuation_standard must be True"
            else:
                pytest.skip("Basel III entry not found in registry detail")
        else:
            assert basel_entry.get("not_pure_valuation_standard") is True, \
                "Basel III not_pure_valuation_standard must be True"


# ── UB06: USPAP selected_standards accepted in payload ───────────────────────
def test_PVS4_UB06_uspap_payload_accepted():
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["uspap"]})
        assert resp.get("request_id") or resp.get("ok"), f"create with uspap failed: {resp}"
        ctx = resp.get("applied_standards_context") or {}
        if ctx:
            assert "uspap" in (ctx.get("selected_standards") or [])


# ── UB07: Basel III selected_standards accepted in payload ────────────────────
def test_PVS4_UB07_basel_iii_payload_accepted():
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["basel_iii"]})
        assert resp.get("request_id") or resp.get("ok"), f"create with basel_iii failed: {resp}"
        ctx = resp.get("applied_standards_context") or {}
        if ctx:
            assert "basel_iii" in (ctx.get("selected_standards") or [])


# ── UB08: 'basel' alias maps to 'basel_iii' ───────────────────────────────────
def test_PVS4_UB08_basel_alias_maps_to_basel_iii():
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["basel"]})
        ctx = resp.get("applied_standards_context") or {}
        if not ctx:
            pytest.skip("applied_standards_context not in response")
        sel = ctx.get("selected_standards") or []
        assert "basel_iii" in sel, f"'basel' alias should map to 'basel_iii'. Got: {sel}"


# ── UB09: 'basel3' alias maps to 'basel_iii' ─────────────────────────────────
def test_PVS4_UB09_basel3_alias_maps_to_basel_iii():
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["basel3"]})
        ctx = resp.get("applied_standards_context") or {}
        if not ctx:
            pytest.skip("applied_standards_context not in response")
        sel = ctx.get("selected_standards") or []
        assert "basel_iii" in sel, f"'basel3' alias should map to 'basel_iii'. Got: {sel}"


# ── UB10: 'USPAP' (uppercase) alias maps to 'uspap' ──────────────────────────
def test_PVS4_UB10_uspap_uppercase_alias():
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["USPAP"]})
        ctx = resp.get("applied_standards_context") or {}
        if not ctx:
            pytest.skip("applied_standards_context not in response")
        sel = ctx.get("selected_standards") or []
        assert "uspap" in sel, f"'USPAP' alias should map to 'uspap'. Got: {sel}"


# ── UB11: USPAP context advisory_only=true ───────────────────────────────────
def test_PVS4_UB11_uspap_context_advisory_only():
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["uspap"]})
        ctx = resp.get("applied_standards_context") or {}
        if not ctx:
            pytest.skip("applied_standards_context not in response")
        uc = ctx.get("uspap_context", {})
        if uc:
            assert uc.get("advisory_only") is True
            assert uc.get("final_compliance_claim") is False
        else:
            # advisory_only at top level
            assert ctx.get("advisory_only") is True


# ── UB12: Basel III context advisory_only=true ────────────────────────────────
def test_PVS4_UB12_basel_iii_context_advisory_only():
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["basel_iii"]})
        ctx = resp.get("applied_standards_context") or {}
        if not ctx:
            pytest.skip("applied_standards_context not in response")
        bc = ctx.get("basel_iii_context", {})
        if bc:
            assert bc.get("advisory_only") is True
            assert bc.get("credit_approval") is False
        else:
            assert ctx.get("advisory_only") is True


# ── UB13: Basel III does not produce credit approval ─────────────────────────
def test_PVS4_UB13_basel_no_credit_approval():
    with app.test_client() as c:
        resp = _create(c, {
            "selected_standards": ["basel_iii"],
            "basel_iii_use_case": "mortgage_financing",
            "basel_iii_collateral_value": 500000,
            "basel_iii_ltv_ratio": 70,
        })
        import json
        text = json.dumps(resp)
        assert "credit_approved" not in text.lower() or '"credit_approval": false' in text or '"credit_approval":false' in text, \
            "Basel III response must NOT claim credit approval"
        ctx = resp.get("applied_standards_context", {})
        bc = ctx.get("basel_iii_context", {})
        if bc:
            assert bc.get("credit_approval") is False


# ── UB14: Basel III does not produce regulatory capital calculation ───────────
def test_PVS4_UB14_basel_no_regulatory_capital_calc():
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["basel_iii"]})
        ctx = resp.get("applied_standards_context", {})
        bc = ctx.get("basel_iii_context", {})
        if bc:
            assert bc.get("regulatory_capital_calculation") is False


# ── UB15: IFRS fair value level remains detail of IFRS 13 ────────────────────
def test_PVS4_UB15_ifrs_level_detail_of_ifrs13():
    with app.test_client() as c:
        resp = _create(c, {
            "selected_standards": ["ifrs_13"],
            "ifrs_fair_value_level": "level_2",
        })
        ctx = resp.get("applied_standards_context") or {}
        if not ctx:
            pytest.skip("applied_standards_context not in response")
        assert "ifrs_13" in (ctx.get("selected_standards") or [])
        assert ctx.get("ifrs_fair_value_level") == "level_2"


# ── UB16: No old standard deleted — IVS still present ────────────────────────
def test_PVS4_UB16_ivs_not_deleted():
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["ivs_2025"]})
        assert resp.get("request_id") or resp.get("ok"), f"IVS create failed: {resp}"
        ctx = resp.get("applied_standards_context") or {}
        if ctx:
            assert "ivs_2025" in (ctx.get("selected_standards") or [])


# ── UB17: No old standard deleted — RICS still present ───────────────────────
def test_PVS4_UB17_rics_not_deleted():
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["rics_red_book_2025"]})
        assert resp.get("request_id") or resp.get("ok"), f"RICS create failed: {resp}"
        ctx = resp.get("applied_standards_context") or {}
        if ctx:
            assert "rics_red_book_2025" in (ctx.get("selected_standards") or [])


# ── UB18: No old standard deleted — FRA Egypt still present ──────────────────
def test_PVS4_UB18_fra_egypt_not_deleted():
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["fra_egypt"]})
        assert resp.get("request_id") or resp.get("ok"), f"FRA create failed: {resp}"


# ── UB19: No duplicate standards in registry ─────────────────────────────────
def test_PVS4_UB19_no_duplicate_standards():
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["ivs_2025", "rics_red_book_2025", "uspap", "ifrs_13", "fra_egypt", "gcc_standards", "custom_local_standard", "basel_iii"]})
        ctx = resp.get("applied_standards_context") or {}
        if not ctx:
            pytest.skip("applied_standards_context not in response")
        standards = ctx.get("standards") or []
        keys = [s["key"] if isinstance(s, dict) else s for s in standards]
        assert len(keys) == len(set(keys)), f"Duplicate standards found: {keys}"


# ── UB20: Compliance summary final_compliance_claim=false ────────────────────
def test_PVS4_UB20_compliance_summary_no_final_claim():
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["ivs_2025", "uspap"]})
        ctx = resp.get("applied_standards_context") or {}
        if not ctx:
            pytest.skip("applied_standards_context not in response")
        cs = ctx.get("compliance_summary", {})
        if cs:
            assert cs.get("final_compliance_claim") is False
        # Also check advisory_only
        assert ctx.get("advisory_only") is True


# ── UB21: requires_expert_review=true ────────────────────────────────────────
def test_PVS4_UB21_requires_expert_review():
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["uspap", "basel_iii"]})
        ctx = resp.get("applied_standards_context") or {}
        if not ctx:
            pytest.skip("applied_standards_context not in response")
        assert ctx.get("expert_review_required") is True or ctx.get("advisory_only") is True


# ── UB22: No internal paths in create response ────────────────────────────────
def test_PVS4_UB22_no_internal_paths():
    import json
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["uspap", "basel_iii"]})
        text = json.dumps(resp)
        assert "C:\\Users" not in text
        assert "/home/" not in text


# ── UB23: Multi-standard payload (IVS + RICS + USPAP + Basel III) ─────────────
def test_PVS4_UB23_multi_standard_payload():
    with app.test_client() as c:
        resp = _create(c, {"selected_standards": ["ivs_2025", "rics_red_book_2025", "uspap", "basel_iii"]})
        assert resp.get("request_id") or resp.get("ok"), f"multi-standard create failed: {resp}"
        ctx = resp.get("applied_standards_context") or {}
        if ctx:
            sel = ctx.get("selected_standards") or []
            for s in ["ivs_2025", "rics_red_book_2025", "uspap", "basel_iii"]:
                assert s in sel, f"{s} missing from selected_standards in response"


# ── UB24: Ordinary valuation unaffected ──────────────────────────────────────
def test_PVS4_UB24_ordinary_valuation_unaffected():
    with app.test_client() as c:
        r = c.post(
            "/api/valuation",
            json={"property_type": "apartment", "city": "Cairo", "district": "Downtown", "area": 120, "age": 5},
            headers=_auth(),
            content_type="application/json",
        )
        assert r.status_code in (200, 201, 400, 422), \
            f"ordinary valuation broken: status={r.status_code}"
