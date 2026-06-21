"""
PSM01-PSM15 — Professional Selector Grouping E2E Tests

Verifies that the professional workspace is organized into two clearly labeled groups:
  Group 1 (quick-selectors-section):  #val-purpose + #asset-type  — common/fast path
  Group 2 (professional-selectors-section): #prof-asset-family + #prof-asset-subtype +
      Purpose Route / Sub-route + Requirements Checklist + Integration Matrix

No option from any selector may be lost.  Both groups must be simultaneously visible.
"""
import pytest


def _goto(page, live_server):
    """Navigate to root — ws-professional is the default active workspace."""
    page.goto(live_server, wait_until="networkidle")


# ── PSM01-02: Both group banners are visible ──────────────────────────────────

def test_PSM01_quick_selectors_section_visible(page, live_server):
    """PSM01: Group 1 banner (quick-selectors-section) is visible."""
    _goto(page, live_server)
    assert page.is_visible('[data-testid="quick-selectors-section"]'), \
        "quick-selectors-section banner must be visible"


def test_PSM02_professional_selectors_section_visible(page, live_server):
    """PSM02: Group 2 banner (professional-selectors-section) is visible."""
    _goto(page, live_server)
    assert page.is_visible('[data-testid="professional-selectors-section"]'), \
        "professional-selectors-section banner must be visible"


# ── PSM03-04: Group 1 quick selectors are visible ────────────────────────────

def test_PSM03_asset_type_visible(page, live_server):
    """PSM03: #asset-type (quick/common asset selector) is visible."""
    _goto(page, live_server)
    assert page.is_visible("#asset-type"), "#asset-type must be visible"


def test_PSM04_val_purpose_visible(page, live_server):
    """PSM04: #val-purpose (quick/common purpose selector) is visible."""
    _goto(page, live_server)
    assert page.is_visible("#val-purpose"), "#val-purpose must be visible"


# ── PSM05-06: Group 2 professional selectors are visible ─────────────────────

def test_PSM05_prof_asset_family_visible(page, live_server):
    """PSM05: #prof-asset-family (professional registry) is visible."""
    _goto(page, live_server)
    assert page.is_visible("#prof-asset-family"), "#prof-asset-family must be visible"


def test_PSM06_prof_asset_subtype_visible(page, live_server):
    """PSM06: #prof-asset-subtype (professional registry) is visible."""
    _goto(page, live_server)
    assert page.is_visible("#prof-asset-subtype"), "#prof-asset-subtype must be visible"


# ── PSM07: Purpose Route visible (Group 2) ───────────────────────────────────

def test_PSM07_prof_purpose_route_visible(page, live_server):
    """PSM07: #prof-purpose-route (professional purpose router) is visible."""
    _goto(page, live_server)
    assert page.is_visible("#prof-purpose-route"), "#prof-purpose-route must be visible"


# ── PSM08-09: No option lost — option counts ─────────────────────────────────

def test_PSM08_asset_type_option_count(page, live_server):
    """PSM08: #asset-type retains all 39 legacy options (none deleted)."""
    _goto(page, live_server)
    count = page.eval_on_selector(
        "#asset-type",
        "el => Array.from(el.options).filter(o => o.value !== '').length"
    )
    assert count >= 39, \
        f"#asset-type should have >= 39 options, got {count}"


def test_PSM09_asset_type_has_key_legacy_options(page, live_server):
    """PSM09: #asset-type carries all key legacy option values."""
    _goto(page, live_server)
    values = page.eval_on_selector(
        "#asset-type",
        "el => Array.from(el.options).map(o => o.value)"
    )
    expected = [
        "شقة سكنية",   # شقة سكنية
        "عمارة سكنية",  # عمارة سكنية
        "أرض فضاء",          # أرض فضاء
        "أرض زراعية",  # أرض زراعية
        "تجاري",                        # تجاري
        "مبنى قائم",    # مبنى قائم
        "prefabricated_factory", "wellness_resort", "educational_asset",
        "littoral_rights", "riparian_rights", "waterway_easement",
        "ملكيات جزئية",  # ملكيات جزئية
    ]
    missing = [v for v in expected if v not in values]
    assert not missing, f"Missing #asset-type options: {missing}"


def test_PSM10_val_purpose_option_count(page, live_server):
    """PSM10: #val-purpose retains all 14 legacy purpose options (none deleted)."""
    _goto(page, live_server)
    count = page.eval_on_selector(
        "#val-purpose",
        "el => Array.from(el.options).filter(o => o.value !== '').length"
    )
    assert count >= 14, \
        f"#val-purpose should have >= 14 options, got {count}"


def test_PSM11_prof_purpose_route_option_count(page, live_server):
    """PSM11: #prof-purpose-route retains all 54 professional purpose options."""
    _goto(page, live_server)
    count = page.eval_on_selector(
        "#prof-purpose-route",
        "el => Array.from(el.options).filter(o => o.value !== '').length"
    )
    assert count >= 54, \
        f"#prof-purpose-route should have >= 54 options, got {count}"


# ── PSM12: Requirements Checklist visible ────────────────────────────────────

def test_PSM12_requirements_checklist_exists(page, live_server):
    """PSM12: Requirements Checklist panel (#es-req-panel) exists in DOM."""
    _goto(page, live_server)
    assert page.query_selector("#es-req-panel") is not None, \
        "#es-req-panel (requirements checklist) must be in DOM"


# ── PSM13: Integration Matrix visible ────────────────────────────────────────

def test_PSM13_integration_matrix_exists(page, live_server):
    """PSM13: Integration Matrix dashboard element exists."""
    _goto(page, live_server)
    assert page.query_selector('[data-testid="professional-matrix-dashboard"]') is not None, \
        "professional-matrix-dashboard must be in DOM"


# ── PSM14-15: Professional family/subtype interaction still works ─────────────

def test_PSM14_family_selection_populates_subtypes(page, live_server):
    """PSM14: Selecting a professional family populates subtype dropdown."""
    _goto(page, live_server)
    page.select_option("#prof-asset-family", value="advanced_industrial_logistics")
    options = page.eval_on_selector(
        "#prof-asset-subtype",
        "el => Array.from(el.options).map(o => o.value).filter(v => v !== '')"
    )
    assert len(options) > 0, "Subtype dropdown should be populated after family selection"
    assert "prefabricated_factory" in options, \
        f"Expected prefabricated_factory in subtypes, got: {options}"


def test_PSM15_subtype_syncs_asset_type(page, live_server):
    """PSM15: Selecting a professional subtype syncs value to #asset-type."""
    _goto(page, live_server)
    page.select_option("#prof-asset-family", value="advanced_industrial_logistics")
    page.select_option("#prof-asset-subtype", value="prefabricated_factory")
    asset_type_val = page.eval_on_selector("#asset-type", "el => el.value")
    assert asset_type_val == "prefabricated_factory", \
        f"Expected #asset-type='prefabricated_factory', got '{asset_type_val}'"
