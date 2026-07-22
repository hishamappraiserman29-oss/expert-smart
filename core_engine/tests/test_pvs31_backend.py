"""
PVS31 — Professional Valuation Section 3.1 Purpose Route Merge: Backend Tests
Tests B01-B15
"""

import re
import pathlib
import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_HTML = (_ROOT / "frontend/index.html").read_text(encoding="utf-8")


def _has(pattern: str) -> bool:
    return bool(re.search(pattern, _HTML, re.S))


# ─── B01 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B01_assignment_purpose_select_present():
    """B01: pvr-vis-assignment-purpose select is present in HTML."""
    assert _has(r'id="pvr-vis-assignment-purpose"'), \
        "pvr-vis-assignment-purpose select not found in HTML"


# ─── B02 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B02_assignment_purpose_label_updated():
    """B02: Label for assignment_purpose is 'الغرض الرئيسي للتقييم' (not old text)."""
    assert _has(r'الغرض الرئيسي للتقييم'), \
        "Updated label 'الغرض الرئيسي للتقييم' not found"


# ─── B03 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B03_purpose_subroute_select_present():
    """B03: pvr-vis-purpose-subroute select is present in HTML."""
    assert _has(r'id="pvr-vis-purpose-subroute"'), \
        "pvr-vis-purpose-subroute select not found in HTML"


# ─── B04 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B04_purpose_subroute_testid_present():
    """B04: pro-val-purpose-subroute-select testid is present in HTML."""
    assert _has(r'data-testid="pro-val-purpose-subroute-select"'), \
        "pro-val-purpose-subroute-select testid not found"


# ─── B05 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B05_purpose_logic_path_hidden():
    """B05: pvr-vis-purpose-logic-path is inside a display:none container."""
    # The div wrapping it has display:none
    assert _has(r'display:none[^>]*>.*?id="pvr-vis-purpose-logic-path"'), \
        "pvr-vis-purpose-logic-path is not inside a display:none container"


# ─── B06 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B06_purpose_logic_path_in_dom():
    """B06: pvr-vis-purpose-logic-path is still present in DOM (not deleted)."""
    assert _has(r'id="pvr-vis-purpose-logic-path"'), \
        "pvr-vis-purpose-logic-path was deleted from DOM — must be preserved"


# ─── B07 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B07_purpose_logic_path_testid_preserved():
    """B07: pro-val-purpose-logic-path-select testid is still in HTML (PVNEW05/06 compat)."""
    count = len(re.findall(r'data-testid="pro-val-purpose-logic-path-select"', _HTML))
    assert count >= 2, \
        f"Expected >=2 instances of pro-val-purpose-logic-path-select, got {count}"


# ─── B08 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B08_purpose_router_block_hidden():
    """B08: pro-val-purpose-router-section is hidden via display:none."""
    assert _has(r'data-testid="pro-val-purpose-router-section"[^>]*display:none'), \
        "pro-val-purpose-router-section is not hidden with display:none"


# ─── B09 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B09_purpose_router_block_in_dom():
    """B09: pro-val-purpose-router-section is still in DOM (not deleted)."""
    assert _has(r'data-testid="pro-val-purpose-router-section"'), \
        "pro-val-purpose-router-section was deleted — must be preserved in DOM"


# ─── B10 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B10_pv_purpose_subroutes_declared():
    """B10: _PV_PURPOSE_SUBROUTES object is declared in JS."""
    assert _has(r'var _PV_PURPOSE_SUBROUTES\s*='), \
        "_PV_PURPOSE_SUBROUTES not declared in JS"


# ─── B11 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B11_update_subroute_function_declared():
    """B11: pvUpdatePurposeSubrouteOptions function is declared."""
    assert _has(r'pvUpdatePurposeSubrouteOptions\s*=\s*function'), \
        "pvUpdatePurposeSubrouteOptions not declared"


# ─── B12 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B12_update_subroute_called_from_onchange():
    """B12: pvUpdatePurposeSubrouteOptions is called in assignment_purpose onchange."""
    assert _has(r'pvUpdatePurposeSubrouteOptions\(\)'), \
        "pvUpdatePurposeSubrouteOptions() not called anywhere"


# ─── B13 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B13_render_guidance_function_declared():
    """B13: pvRenderPurposeInlineGuidance function is declared."""
    assert _has(r'pvRenderPurposeInlineGuidance\s*=\s*function'), \
        "pvRenderPurposeInlineGuidance not declared"


# ─── B14 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B14_mortgage_subroute_options_present():
    """B14: mortgage_financing subroute includes collateral_valuation."""
    assert _has(r"mortgage_financing.*?collateral_valuation"), \
        "mortgage_financing subroute collateral_valuation not found in _PV_PURPOSE_SUBROUTES"


# ─── B15 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B15_purpose_subroute_in_payload():
    """B15: purpose_subroute is included in the pvSubmitNewRequest payload."""
    assert _has(r"purpose_subroute\s*:.*?purposeSubroute"), \
        "purpose_subroute not included in pvSubmitNewRequest payload"


# ─── B16 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B16_no_dloc_dlom_in_subroute_options():
    """B16: DLOC/DLOM do not appear as selectable purpose_subroute values in _PV_PURPOSE_SUBROUTES."""
    # Check that DLOC/DLOM are not listed as subroute values (they appear only in partial interest panel)
    sub_block_match = re.search(r'var _PV_PURPOSE_SUBROUTES\s*=\s*\{(.+?)\};\s*\n', _HTML, re.S)
    if sub_block_match:
        block = sub_block_match.group(1)
        assert 'dloc' not in block.lower() and 'dlom' not in block.lower(), \
            "DLOC/DLOM should not appear as subroute values in _PV_PURPOSE_SUBROUTES"


# ─── B17 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B17_sale_purchase_subroute_options():
    """B17: sale_purchase subroute includes seller_side and buyer_side."""
    assert _has(r"sale_purchase.*?seller_side"), \
        "sale_purchase seller_side not found in _PV_PURPOSE_SUBROUTES"
    assert _has(r"sale_purchase.*?buyer_side"), \
        "sale_purchase buyer_side not found in _PV_PURPOSE_SUBROUTES"


# ─── B18 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B18_tax_appeal_subroute_options():
    """B18: tax_appeal subroute includes property_tax_appeal."""
    assert _has(r"tax_appeal.*?property_tax_appeal"), \
        "tax_appeal property_tax_appeal not found in _PV_PURPOSE_SUBROUTES"


# ─── B19 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B19_partial_interest_subroute_options():
    """B19: partial_interest_valuation subroute includes minority_interest."""
    assert _has(r"partial_interest_valuation.*?minority_interest"), \
        "partial_interest_valuation minority_interest not found in _PV_PURPOSE_SUBROUTES"


# ─── B20 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B20_helper_text_updated():
    """B20: Section 3.1 helper text is the new text (not old text)."""
    assert _has(r'اختر الغرض الرئيسي للتقييم، ثم اختر المسار الفرعي المناسب له'), \
        "New helper text for Section 3.1 not found"
    # Old text should NOT appear in this section
    old_helper = _HTML.find('اختر السبب التجاري أو القانوني الرئيسي للتقييم')
    assert old_helper == -1, "Old helper text was not updated"


# ─── B21 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B21_legacy_options_preserved():
    """B21: Legacy purpose options are preserved (financing_mortgage, court_dispute, etc.)."""
    assert _has(r'value="financing_mortgage"'), "financing_mortgage option deleted"
    assert _has(r'value="court_dispute"'), "court_dispute option deleted"
    assert _has(r'value="liquidation_restructuring"'), "liquidation_restructuring option deleted"
    assert _has(r'value="inheritance_partition"'), "inheritance_partition option deleted"


# ─── B22 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B22_new_canonical_options_added():
    """B22: New canonical purpose options are present (mortgage_financing, litigation_court, etc.)."""
    assert _has(r'value="mortgage_financing"'), "mortgage_financing option not added"
    assert _has(r'value="litigation_court"'), "litigation_court option not added"
    assert _has(r'value="forced_liquidation"'), "forced_liquidation option not added"
    assert _has(r'value="securitization"'), "securitization option not added"
    assert _has(r'value="asset_swap"'), "asset_swap option not added"


# ─── B23 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B23_no_methodology_in_assignment_purpose():
    """B23: Methodology values (DCF, sales_comparison, HABU) are not in pvr-vis-assignment-purpose."""
    # Check the assignment_purpose select block
    ap_match = re.search(
        r'id="pvr-vis-assignment-purpose".*?</select>', _HTML, re.S
    )
    assert ap_match, "pvr-vis-assignment-purpose select not found"
    ap_block = ap_match.group(0)
    assert 'dcf' not in ap_block.lower(), "DCF found in assignment_purpose options"
    assert 'sales_comparison' not in ap_block.lower(), "sales_comparison found in assignment_purpose"
    assert 'market_value_with_habu' not in ap_block.lower(), "HABU found in assignment_purpose"


# ─── B24 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B24_no_standards_in_section_3_1():
    """B24: IVS/RICS/IFRS not shown inside Section 3.1 (they belong to Section 4)."""
    # Check the purpose logical section block
    block_match = re.search(
        r'data-testid="pro-val-purpose-logical-section".*?</div>\s*</div>\s*<!-- /pro-val-purpose-main-subsection',
        _HTML, re.S
    )
    if block_match:
        block = block_match.group(0)
        assert 'IVS' not in block, "IVS found inside Section 3.1 block"
        assert 'RICS' not in block, "RICS found inside Section 3.1 block"


# ─── B25 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B25_inline_guidance_panel_present():
    """B25: pvr-purpose-inline-guidance element is present in HTML."""
    assert _has(r'id="pvr-purpose-inline-guidance"'), \
        "pvr-purpose-inline-guidance element not found"


# ─── B26 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B26_purpose_guidance_dict_declared():
    """B26: _PV_PURPOSE_GUIDANCE object declared in JS."""
    assert _has(r'var _PV_PURPOSE_GUIDANCE\s*='), \
        "_PV_PURPOSE_GUIDANCE not declared"


# ─── B27 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B27_section3_flow_function_declared():
    """B27: pvUpdateSection3PurposeFlow function is declared."""
    assert _has(r'pvUpdateSection3PurposeFlow\s*=\s*function'), \
        "pvUpdateSection3PurposeFlow not declared"


# ─── B28 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B28_purpose_router_summary_text_hidden():
    """B28: 'اختر مسار الغرض لعرض الوصف والمعايير المطبقة' is inside hidden block."""
    # This text is inside pro-val-purpose-router-section which is now display:none
    text_idx = _HTML.find('اختر مسار الغرض لعرض الوصف والمعايير المطبقة')
    if text_idx >= 0:
        # Find the enclosing pro-val-purpose-router-section start
        section_idx = _HTML.rfind('pro-val-purpose-router-section', 0, text_idx)
        assert section_idx >= 0, "Router summary text not inside purpose-router-section"
        # Verify that section has display:none
        section_tag = _HTML[section_idx:section_idx + 300]
        assert 'display:none' in section_tag, "Router summary text is visible — should be hidden"


# ─── B29 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B29_purpose_subroute_placeholder_text():
    """B29: pvr-vis-purpose-subroute has correct placeholder text."""
    assert _has(r'اختر الغرض الرئيسي أولاً'), \
        "Purpose subroute placeholder 'اختر الغرض الرئيسي أولاً' not found"


# ─── B30 ──────────────────────────────────────────────────────────────────────
def test_PVS31_B30_purpose_subroute_var_declared():
    """B30: purposeSubroute variable is declared in pvSubmitNewRequest."""
    assert _has(r"var purposeSubroute\s*="), \
        "purposeSubroute variable not declared in pvSubmitNewRequest"
