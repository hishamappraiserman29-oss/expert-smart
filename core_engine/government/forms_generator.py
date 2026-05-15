"""
forms_generator.py — Government Forms Generator

Generate official government forms for property valuations.
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class GovernmentForm(str, Enum):
    CBE_FORM_101 = "cbe_101"              # CBE Collateral Valuation Form
    TAX_FORM_50 = "tax_50"                # Tax Authority Property Valuation Form
    EGFSA_FORM_30 = "egfsa_30"            # EGFSA Fair Value Assessment Form
    PROPERTY_REGISTRATION = "registration"  # Property Registration Form
    LOAN_VALUATION_FORM = "loan_form"      # Bank Loan Valuation Form


def _fmt_money(value: Any, default: str = "N/A") -> str:
    """Format a numeric value as currency string, or return default."""
    if isinstance(value, (int, float)):
        return f"{value:,.0f}"
    return default


def _fmt_ltv(loan: Any, val: Any, default: str = "N/A") -> str:
    """Format loan-to-value ratio as percentage string."""
    if isinstance(loan, (int, float)) and isinstance(val, (int, float)) and val > 0:
        return f"{loan / val * 100:.1f}%"
    return default


class FormsGenerator:
    """Generate official government forms for property valuations."""

    # ------------------------------------------------------------------
    # CBE Form 101
    # ------------------------------------------------------------------

    def generate_cbe_form_101(
        self,
        property_data: Dict[str, Any],
        valuation_result: Dict[str, Any],
        appraiser_info: Dict[str, Any],
    ) -> str:
        """Generate CBE Form 101 — Collateral Valuation for Real Property."""

        loan_amount = property_data.get("loan_amount")
        primary_value = valuation_result.get("primary_value")

        form = (
            f"CENTRAL BANK OF EGYPT — FORM CBE 101\n"
            f"COLLATERAL VALUATION FORM FOR REAL PROPERTY\n"
            f"{'=' * 64}\n"
            f"\n1. PROPERTY IDENTIFICATION\n"
            f"   Property ID:         {property_data.get('property_id', 'N/A')}\n"
            f"   Address:             {property_data.get('address', 'N/A')}\n"
            f"   City:                {property_data.get('city', 'N/A')}\n"
            f"   Area (sqm):          {property_data.get('area_sqm', 'N/A')}\n"
            f"   Property Type:       {property_data.get('property_type', 'N/A')}\n"
            f"\n2. VALUATION DETAILS\n"
            f"   Valuation Date:      {valuation_result.get('valuation_date', 'N/A')}\n"
            f"   Valuation Method:    {valuation_result.get('method', 'Comparative')}\n"
            f"   Primary Value (EGP): {_fmt_money(primary_value)}\n"
            f"   Confidence Level:    {valuation_result.get('confidence', 'High')}\n"
            f"\n3. COLLATERAL ASSESSMENT\n"
            f"   Collateral Value (EGP): {_fmt_money(primary_value)}\n"
            f"   Loan Amount (EGP):      {_fmt_money(loan_amount)}\n"
            f"   LTV Ratio:              {_fmt_ltv(loan_amount, primary_value)}\n"
            f"\n4. RISK ASSESSMENT\n"
            f"   Location Risk:       {property_data.get('location_risk', 'Low')}\n"
            f"   Market Risk:         {property_data.get('market_risk', 'Low')}\n"
            f"   Property Condition:  {property_data.get('condition', 'Good')}\n"
            f"   Overall Risk Rating: {property_data.get('risk_rating', 'Low')}\n"
            f"\n5. APPRAISER INFORMATION\n"
            f"   Appraiser Name:      {appraiser_info.get('name', 'N/A')}\n"
            f"   License Number:      {appraiser_info.get('license', 'N/A')}\n"
            f"   CBE Approval:        {appraiser_info.get('cbe_approved', 'Yes')}\n"
            f"   Signature:           _______________________\n"
            f"   Date:                {datetime.now().strftime('%Y-%m-%d')}\n"
            f"\n6. CERTIFICATION\n"
            f"   I certify that this valuation has been completed in accordance\n"
            f"   with Central Bank of Egypt standards.\n"
            f"\n7. AUTHORIZATION\n"
            f"   Bank Official Name:      _______________________\n"
            f"   Bank Official Signature: _______________________\n"
            f"   Date:                    _______________________\n"
            f"\n{'=' * 64}\n"
            f"Form CBE-101 | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Official Use Only\n"
        )
        return form

    # ------------------------------------------------------------------
    # Tax Authority Form 50
    # ------------------------------------------------------------------

    def generate_tax_form_50(
        self,
        property_data: Dict[str, Any],
        tax_result: Dict[str, Any],
        owner_info: Dict[str, Any],
    ) -> str:
        """Generate Tax Authority Form 50 — Property Valuation Declaration."""

        form = (
            f"EGYPTIAN TAX AUTHORITY — FORM 50\n"
            f"PROPERTY VALUATION DECLARATION\n"
            f"{'=' * 64}\n"
            f"\n1. TAXPAYER INFORMATION\n"
            f"   Name:                {owner_info.get('name', 'N/A')}\n"
            f"   ID Number:           {owner_info.get('id_number', 'N/A')}\n"
            f"   Address:             {owner_info.get('address', 'N/A')}\n"
            f"\n2. PROPERTY INFORMATION\n"
            f"   Property ID:         {property_data.get('property_id', 'N/A')}\n"
            f"   Location:            {property_data.get('address', 'N/A')}\n"
            f"   Area (sqm):          {property_data.get('area_sqm', 'N/A')}\n"
            f"   Property Type:       {property_data.get('property_type', 'N/A')}\n"
            f"   Tax Classification:  {tax_result.get('tax_classification', 'N/A')}\n"
            f"\n3. VALUATION DETAILS\n"
            f"   Assessed Value (EGP): {_fmt_money(tax_result.get('assessed_value'))}\n"
            f"   Valuation Method:     {property_data.get('valuation_method', 'Market Approach')}\n"
            f"   Valuation Date:       {tax_result.get('calculated_at', 'N/A')}\n"
            f"\n4. TAX LIABILITY\n"
            f"   Annual Property Tax (EGP): {_fmt_money(tax_result.get('annual_tax'))}\n"
            f"   Capital Gains Tax (EGP):   {_fmt_money(tax_result.get('estimated_capital_gains_tax', 0))}\n"
            f"   Total Estimated Tax (EGP): {_fmt_money(tax_result.get('total_estimated_tax'))}\n"
            f"\n5. DECLARATIONS\n"
            f"   I declare that the information provided is true and complete.\n"
            f"   Owner Signature:     _______________________\n"
            f"   Date:                {datetime.now().strftime('%Y-%m-%d')}\n"
            f"\n6. OFFICIAL USE ONLY\n"
            f"   Tax Officer Name:    _______________________\n"
            f"   Tax Officer Sig:     _______________________\n"
            f"   Assessment Date:     _______________________\n"
            f"   Final Tax Amount:    ___________ EGP\n"
            f"\n{'=' * 64}\n"
            f"Form 50 | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        return form

    # ------------------------------------------------------------------
    # EGFSA Form 30
    # ------------------------------------------------------------------

    def generate_egfsa_form_30(
        self,
        property_data: Dict[str, Any],
        valuation_result: Dict[str, Any],
        expert_info: Dict[str, Any],
    ) -> str:
        """Generate EGFSA Form 30 — Fair Value Assessment (IFRS 13)."""

        form = (
            f"EGYPTIAN FINANCIAL SUPERVISORY AUTHORITY — FORM 30\n"
            f"FAIR VALUE ASSESSMENT FORM (IFRS 13 Compliance)\n"
            f"{'=' * 64}\n"
            f"\n1. PROPERTY IDENTIFICATION\n"
            f"   Asset ID:            {property_data.get('asset_id', 'N/A')}\n"
            f"   Location:            {property_data.get('address', 'N/A')}\n"
            f"   Classification:      {property_data.get('classification', 'N/A')}\n"
            f"\n2. VALUATION SUMMARY\n"
            f"   Fair Value (EGP):    {_fmt_money(valuation_result.get('fair_value'))}\n"
            f"   Valuation Level:     {valuation_result.get('valuation_level', 'Level 2')}\n"
            f"   Valuation Approach:  {valuation_result.get('approach', 'Market')}\n"
            f"\n3. VALUATION INPUTS\n"
            f"   Input Category:      {valuation_result.get('input_category', 'Observable')}\n"
            f"   Confidence Score:    {valuation_result.get('confidence', 'High')}\n"
            f"   Hierarchy Level:     {valuation_result.get('hierarchy', '2')}\n"
            f"\n4. EXPERT CERTIFICATION\n"
            f"   Expert Name:         {expert_info.get('name', 'N/A')}\n"
            f"   EGFSA Certification: {expert_info.get('egfsa_cert', 'Yes')}\n"
            f"   Cert Number:         {expert_info.get('cert_number', 'N/A')}\n"
            f"\n5. COMPLIANCE STATEMENT\n"
            f"   This fair value assessment has been prepared in accordance with\n"
            f"   IFRS 13 standards and EGFSA guidelines for financial reporting.\n"
            f"   Expert Signature:    _______________________\n"
            f"   Date:                {datetime.now().strftime('%Y-%m-%d')}\n"
            f"\n{'=' * 64}\n"
            f"Form EGFSA-30 | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Confidential — For Official Use Only\n"
        )
        return form


forms_generator = FormsGenerator()
