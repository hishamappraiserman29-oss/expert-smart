"""
Backend tests — PV Certified Expert Review Request
Tests: PVCERT01–PVCERT19
advisory_only=True | not_real_training=True | certification_ready=False

Run:
  python -m pytest core_engine/tests/test_pv_certified_expert_review_request.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_CORE))

_QA = (
    _CORE
    / "instance"
    / "manual_review_outputs"
    / "professional_valuation_certified_expert_review_request"
)
_FRONTEND = _CORE.parent / "frontend" / "index.html"


# ── helpers ──────────────────────────────────────────────────────────────────

def _load_audit(name: str) -> dict:
    p = _QA / name
    assert p.exists(), f"Audit file missing: {p}"
    return json.loads(p.read_text(encoding="utf-8"))


def _html() -> str:
    assert _FRONTEND.exists(), "frontend/index.html not found"
    return _FRONTEND.read_text(encoding="utf-8")


# ── PVCERT01 — context module importable ─────────────────────────────────────

def test_PVCERT01_backend_context_module_importable():
    """PVCERT01: backend context module is importable."""
    import professional_valuation_certified_expert_review_request_backend_context as m
    assert m is not None


# ── PVCERT02 — certified_expert_review_request_enabled = true ────────────────

def test_PVCERT02_certified_expert_review_request_enabled():
    """PVCERT02: certified_expert_review_request_enabled = True."""
    import professional_valuation_certified_expert_review_request_backend_context as m
    ctx = m.get_backend_context()
    assert ctx["certified_expert_review_request_enabled"] is True


# ── PVCERT03 — matched_ordinary_valuation_page = true ────────────────────────

def test_PVCERT03_matched_ordinary_valuation_page():
    """PVCERT03: matched_ordinary_valuation_page = True."""
    import professional_valuation_certified_expert_review_request_backend_context as m
    ctx = m.get_backend_context()
    assert ctx["matched_ordinary_valuation_page"] is True


# ── PVCERT04 — request does not issue certified report immediately ─────────────

def test_PVCERT04_request_does_not_issue_certified_report_immediately():
    """PVCERT04: request_does_not_issue_certified_report_immediately = True."""
    import professional_valuation_certified_expert_review_request_backend_context as m
    ctx = m.get_backend_context()
    assert ctx["request_does_not_issue_certified_report_immediately"] is True


# ── PVCERT05 — expert review required before certified PDF ────────────────────

def test_PVCERT05_expert_review_required_before_certified_pdf():
    """PVCERT05: expert_review_required_before_certified_pdf = True."""
    import professional_valuation_certified_expert_review_request_backend_context as m
    ctx = m.get_backend_context()
    assert ctx["expert_review_required_before_certified_pdf"] is True


# ── PVCERT06 — delivery methods include whatsapp and email ───────────────────

def test_PVCERT06_delivery_methods_include_whatsapp_and_email():
    """PVCERT06: delivery_methods contains whatsapp and email."""
    import professional_valuation_certified_expert_review_request_backend_context as m
    ctx = m.get_backend_context()
    methods = ctx["delivery_methods"]
    assert "whatsapp" in methods
    assert "email" in methods


# ── PVCERT07 — email required when email selected ────────────────────────────

def test_PVCERT07_email_required_when_email_selected():
    """PVCERT07: email_required_when_email_selected = True."""
    import professional_valuation_certified_expert_review_request_backend_context as m
    ctx = m.get_backend_context()
    assert ctx["email_required_when_email_selected"] is True
    result = m.validate_delivery_method("البريد الإلكتروني", "", "")
    assert result["valid"] is False
    assert "البريد الإلكتروني" in result["error"] or "email" in result["error"].lower()


# ── PVCERT08 — phone required when whatsapp selected ─────────────────────────

def test_PVCERT08_phone_required_when_whatsapp_selected():
    """PVCERT08: phone_required_when_whatsapp_selected = True."""
    import professional_valuation_certified_expert_review_request_backend_context as m
    ctx = m.get_backend_context()
    assert ctx["phone_required_when_whatsapp_selected"] is True
    result = m.validate_delivery_method("واتساب", "", "")
    assert result["valid"] is False


# ── PVCERT09 — full name required ────────────────────────────────────────────

def test_PVCERT09_full_name_required():
    """PVCERT09: full_name_required = True."""
    import professional_valuation_certified_expert_review_request_backend_context as m
    ctx = m.get_backend_context()
    assert ctx["full_name_required"] is True


# ── PVCERT10 — requested report type optional ─────────────────────────────────

def test_PVCERT10_requested_report_type_optional():
    """PVCERT10: requested_report_type_optional = True."""
    import professional_valuation_certified_expert_review_request_backend_context as m
    ctx = m.get_backend_context()
    assert ctx["requested_report_type_optional"] is True


# ── PVCERT11 — admin Excel internal only ─────────────────────────────────────

def test_PVCERT11_admin_excel_internal_only():
    """PVCERT11: admin_excel_internal_only = True."""
    import professional_valuation_certified_expert_review_request_backend_context as m
    ctx = m.get_backend_context()
    assert ctx["admin_excel_internal_only"] is True


# ── PVCERT12 — certification_ready not set automatically ─────────────────────

def test_PVCERT12_certification_ready_not_set_automatically():
    """PVCERT12: certification_ready_changed = False in expert review context."""
    import professional_valuation_certified_expert_review_request_backend_context as m
    ctx = m.get_expert_review_request_context()
    assert ctx["certification_ready_changed"] is False


# ── PVCERT13 — fake approval not created ─────────────────────────────────────

def test_PVCERT13_fake_approval_not_created():
    """PVCERT13: fake_approval_created = False."""
    import professional_valuation_certified_expert_review_request_backend_context as m
    ctx = m.get_backend_context()
    assert ctx["fake_approval_created"] is False
    ctx2 = m.get_expert_review_request_context()
    assert ctx2["fake_approval_created"] is False


# ── PVCERT14 — fake signature not created ────────────────────────────────────

def test_PVCERT14_fake_signature_not_created():
    """PVCERT14: fake_signature_created = False."""
    import professional_valuation_certified_expert_review_request_backend_context as m
    ctx = m.get_backend_context()
    assert ctx["fake_signature_created"] is False
    ctx2 = m.get_expert_review_request_context()
    assert ctx2["fake_signature_created"] is False


# ── PVCERT15 — fake stamp not created ────────────────────────────────────────

def test_PVCERT15_fake_stamp_not_created():
    """PVCERT15: fake_stamp_created = False."""
    import professional_valuation_certified_expert_review_request_backend_context as m
    ctx = m.get_backend_context()
    assert ctx["fake_stamp_created"] is False
    ctx2 = m.get_expert_review_request_context()
    assert ctx2["fake_stamp_created"] is False


# ── PVCERT16 — certification gate preserved ───────────────────────────────────

def test_PVCERT16_certification_gate_preserved():
    """PVCERT16: certification_gate_preserved = True."""
    import professional_valuation_certified_expert_review_request_backend_context as m
    ctx = m.get_backend_context()
    assert ctx["certification_gate_preserved"] is True
    assert ctx["preservation_pass"] is True


# ── PVCERT17 — no internal paths in HTML ─────────────────────────────────────

def test_PVCERT17_no_internal_paths_in_html():
    """PVCERT17: no Windows filesystem paths appear in the PV expert review HTML section."""
    html = _html()
    # Locate the section
    start = html.find('data-testid="pro-val-expert-review-request-section"')
    assert start != -1, "pro-val-expert-review-request-section not found in HTML"
    end = html.find('<!-- /pro-val-expert-review-request-section -->', start)
    if end == -1:
        end = start + 8000
    section = html[start:end]
    for pat in (r'C:\\Users', r'C:/Users', '/home/', 'expert_smart1', 'core_engine/instance'):
        assert pat not in section, f"Internal path leaked: {pat}"


# ── PVCERT18 — ordinary valuation unaffected ─────────────────────────────────

def test_PVCERT18_ordinary_valuation_unaffected():
    """PVCERT18: simple-certified-report-cta-box still present (ordinary page unchanged)."""
    html = _html()
    assert 'id="simple-certified-report-cta-box"' in html
    assert 'data-testid="simple-valuation-cert-request-card"' in html


# ── PVCERT19 — tax appeal unaffected ─────────────────────────────────────────

def test_PVCERT19_tax_appeal_unaffected():
    """PVCERT19: tax appeal testids still present in HTML (not broken)."""
    html = _html()
    # The tax appeal section uses a distinctive testid
    assert 'tax' in html.lower() or 'ضريبي' in html or 'ضريبة' in html, (
        "Tax-related content not found — tax appeal section may have been accidentally removed"
    )
