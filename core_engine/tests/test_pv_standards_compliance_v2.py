"""
Standards Compliance v2 — test suite
50 tests SC2-01 through SC2-50.
Run: python -m pytest tests/test_pv_standards_compliance_v2.py -q
"""
from __future__ import annotations

import json
import pathlib
import sys

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


def _read_audit(name: str) -> dict:
    p = _AUD / name
    assert p.exists(), f"Audit file missing: {name}"
    return json.loads(p.read_text(encoding="utf-8"))


def _user_html() -> str:
    return (_ARTS / f"compliance_v2_{_CID}_user.html").read_text(encoding="utf-8")


def _admin_html() -> str:
    return (_ARTS / f"compliance_v2_{_CID}_admin.html").read_text(encoding="utf-8")


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


# ── SC2-29–37: Physical artifacts ─────────────────────────────────────────────

def test_SC2_29_user_html_exists():
    assert (_ARTS / f"compliance_v2_{_CID}_user.html").exists()


def test_SC2_30_admin_html_exists():
    assert (_ARTS / f"compliance_v2_{_CID}_admin.html").exists()


def test_SC2_31_user_pdf_exists():
    assert (_ARTS / f"compliance_v2_{_CID}_user.pdf").exists()


def test_SC2_32_admin_pdf_exists():
    assert (_ARTS / f"compliance_v2_{_CID}_admin.pdf").exists()


def test_SC2_33_admin_excel_exists():
    assert (_ARTS / f"compliance_v2_{_CID}_admin.xlsx").exists()


def test_SC2_34_user_html_min_size():
    p = _ARTS / f"compliance_v2_{_CID}_user.html"
    assert p.stat().st_size >= 8_000, f"User HTML too small: {p.stat().st_size}"


def test_SC2_35_admin_html_larger_than_user():
    user  = (_ARTS / f"compliance_v2_{_CID}_user.html").stat().st_size
    admin = (_ARTS / f"compliance_v2_{_CID}_admin.html").stat().st_size
    assert admin > user, f"Admin ({admin}B) not larger than user ({user}B)"


def test_SC2_36_user_pdf_valid():
    data = (_ARTS / f"compliance_v2_{_CID}_user.pdf").read_bytes()[:4]
    assert data == b"%PDF"


def test_SC2_37_admin_excel_min_size():
    p = _ARTS / f"compliance_v2_{_CID}_admin.xlsx"
    assert p.stat().st_size >= 5_000


# ── SC2-38–46: HTML content correctness ──────────────────────────────────────

def test_SC2_38_case_id_in_user_html():
    assert _CID in _user_html()


def test_SC2_39_sar_no_egp_user():
    html = _user_html()
    assert "SAR" in html
    assert "EGP" not in html


def test_SC2_40_user_watermark_correct():
    html = _user_html()
    assert "استرشادي" in html
    assert "للمراجعة الداخلية فقط" not in html


def test_SC2_41_admin_watermark_in_admin():
    assert "للمراجعة الداخلية فقط" in _admin_html()


def test_SC2_42_sig_gate_in_both():
    sig = "لم يُوقَّع بعد"
    assert sig in _user_html()
    assert sig in _admin_html()


def test_SC2_43_advisory_flag_in_both():
    for variant, html in (("user", _user_html()), ("admin", _admin_html())):
        assert "advisory_only" in html, f"advisory_only missing from {variant}"


def test_SC2_44_no_admin_marker_in_user():
    assert 'class="admin-only-marker"' not in _user_html()


def test_SC2_45_admin_marker_in_admin():
    assert 'class="admin-only-marker"' in _admin_html()


def test_SC2_46_ml_draft_label_in_user():
    html = _user_html()
    assert "ml-draft-tag" in html or "اقتراح ML" in html or "النموذج غير جاهز" in html


# ── SC2-47–50: Audit JSONs ────────────────────────────────────────────────────

def test_SC2_47_cross_format_passes():
    d = _read_audit("compliance_v2_cross_format.json")
    mismatches = d.get("mismatches", [])
    assert d.get("pass") is True, f"Cross-format failed; mismatches={mismatches}"


def test_SC2_48_excel_sheets_ge_30():
    d = _read_audit("compliance_v2_visual_qa_report.json")
    count = d.get("excel", {}).get("sheet_count", 0)
    assert count >= 30, f"Expected >=30 sheets, got {count}"


def test_SC2_49_screenshots_dir_has_pngs():
    shots = list(_SS.rglob("*.png"))
    assert len(shots) >= 1, "No screenshot PNGs found"


def test_SC2_50_governance_flags_in_report():
    d = _read_audit("compliance_v2_visual_qa_report.json")
    gov = d.get("governance", {})
    assert gov.get("advisory_only") is True
    assert gov.get("fake_signature_created") is False
    assert gov.get("ml_auto_decision") is False
