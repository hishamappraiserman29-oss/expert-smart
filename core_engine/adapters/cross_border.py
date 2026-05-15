"""
cross_border.py — Cross-Border Compliance Framework (Phase 9.2)

Multi-currency support and exchange rate disclosure for international
valuations.  Additive layer — no Phase 4-8 logic is modified.

Classes:
    Currency                 — Enum of supported currencies
    ExchangeRateAssumption   — Dataclass documenting a single exchange rate
    CrossBorderDisclosure    — Dataclass capturing full cross-border disclosure
    CrossBorderBuilder       — Factory for domestic and cross-border disclosures
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional


# ── Currency enum ─────────────────────────────────────────────────────────────

class Currency(Enum):
    """Supported currencies for cross-border valuations."""

    EGP = "EGP"  # Egyptian Pound (primary)
    USD = "USD"  # US Dollar
    EUR = "EUR"  # Euro
    GBP = "GBP"  # British Pound
    AED = "AED"  # UAE Dirham (nearby region)
    SAR = "SAR"  # Saudi Riyal (nearby region)

    def symbol(self) -> str:
        """Return currency symbol."""
        symbols = {
            "EGP": "£",
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "AED": "د.إ",
            "SAR": "﷼",
        }
        return symbols.get(self.value, self.value)


# ── Exchange rate assumption ───────────────────────────────────────────────────

@dataclass
class ExchangeRateAssumption:
    """Exchange rate assumption for cross-border valuation."""

    from_currency: Currency
    to_currency: Currency
    rate: float              # from_currency → to_currency
    effective_date: date
    source: str

    currency_risk_disclosure: str = ""

    def format_rate(self) -> str:
        """Format rate for display."""
        return f"1 {self.from_currency.value} = {self.rate:.4f} {self.to_currency.value}"

    def convert(self, amount: float) -> float:
        """Convert amount using this rate."""
        return amount * self.rate

    def to_dict(self) -> Dict:
        return {
            "from_currency":   self.from_currency.value,
            "to_currency":     self.to_currency.value,
            "rate":            self.rate,
            "effective_date":  self.effective_date.isoformat(),
            "source":          self.source,
            "formatted_rate":  self.format_rate(),
        }


# ── Cross-border disclosure ───────────────────────────────────────────────────

@dataclass
class CrossBorderDisclosure:
    """Cross-border valuation disclosure."""

    subject_property_currency: Currency = Currency.EGP
    reporting_currency: Currency = Currency.EGP

    exchange_rate_assumption: Optional[ExchangeRateAssumption] = None

    property_location_country: str = "Egypt"
    valuation_purpose_country: str = "Egypt"

    currency_risk_statement: str = ""

    reporting_assumptions: List[str] = field(default_factory=list)

    primary_value_egp: float = 0.0
    primary_value_usd: float = 0.0
    primary_value_eur: float = 0.0

    certification_statement: str = ""

    def to_dict(self) -> Dict:
        """Convert to JSON-serialisable dict."""
        return {
            "subject_property_currency": self.subject_property_currency.value,
            "reporting_currency":        self.reporting_currency.value,
            "property_location_country": self.property_location_country,
            "valuation_purpose_country": self.valuation_purpose_country,
            "exchange_rate":             self.exchange_rate_assumption.to_dict()
                                         if self.exchange_rate_assumption else None,
            "currency_risk_statement":   self.currency_risk_statement,
            "reporting_assumptions":     self.reporting_assumptions,
            "primary_value_egp":         self.primary_value_egp,
            "primary_value_usd":         self.primary_value_usd,
            "primary_value_eur":         self.primary_value_eur,
        }


# ── Builder ───────────────────────────────────────────────────────────────────

class CrossBorderBuilder:
    """Build cross-border compliance disclosures."""

    def __init__(self) -> None:
        self.disclosures: Dict[str, CrossBorderDisclosure] = {}

    # ── Domestic EGP ─────────────────────────────────────────────────────────

    def domestic_egp(
        self,
        primary_value: float,
        property_country: str = "Egypt",
    ) -> CrossBorderDisclosure:
        """Build disclosure for domestic EGP valuation (no currency conversion)."""
        disclosure = CrossBorderDisclosure(
            subject_property_currency=Currency.EGP,
            reporting_currency=Currency.EGP,
            property_location_country=property_country,
            valuation_purpose_country=property_country,
            primary_value_egp=primary_value,
            currency_risk_statement=(
                "Property and valuation both in Egyptian Pounds. No currency risk."
            ),
            reporting_assumptions=[
                "Valuation undertaken and reported in Egyptian Pounds (EGP)",
                "Property located in Egypt",
                "No currency conversion applied",
            ],
            certification_statement=(
                "This valuation is expressed in Egyptian Pounds (EGP). "
                "No currency conversion has been applied. "
                "The valuation is valid only in the currency stated."
            ),
        )
        self.disclosures["domestic"] = disclosure
        return disclosure

    # ── Cross-border USD ──────────────────────────────────────────────────────

    def cross_border_usd(
        self,
        primary_value_egp: float,
        exchange_rate: float,               # EGP per 1 USD
        rate_source: str = "Central Bank of Egypt",
        rate_date: Optional[date] = None,
    ) -> CrossBorderDisclosure:
        """Build disclosure for EGP → USD cross-border valuation."""
        if rate_date is None:
            rate_date = date.today()

        primary_value_usd = primary_value_egp / exchange_rate
        egp_per_usd_inv   = 1 / exchange_rate   # 1 EGP = X USD

        rate_assumption = ExchangeRateAssumption(
            from_currency=Currency.EGP,
            to_currency=Currency.USD,
            rate=egp_per_usd_inv,
            effective_date=rate_date,
            source=rate_source,
            currency_risk_disclosure=(
                f"Valuation converted from EGP to USD at rate of "
                f"1 EGP = {egp_per_usd_inv:.4f} USD. "
                f"Exchange rate obtained from {rate_source} on {rate_date.isoformat()}. "
                f"Currency fluctuations may affect value if property is subsequently "
                f"valued in USD or another currency."
            ),
        )

        disclosure = CrossBorderDisclosure(
            subject_property_currency=Currency.EGP,
            reporting_currency=Currency.USD,
            exchange_rate_assumption=rate_assumption,
            property_location_country="Egypt",
            valuation_purpose_country="International",
            primary_value_egp=primary_value_egp,
            primary_value_usd=primary_value_usd,
            currency_risk_statement=(
                f"Property valued in Egyptian Pounds "
                f"(EGP {primary_value_egp:,.0f}) and converted to USD. "
                f"Exchange rate risk: future valuations at different rates may show "
                f"different results. "
                f"If property is refinanced or resold in future, exchange rate may have "
                f"changed significantly."
            ),
            reporting_assumptions=[
                "Primary valuation in Egyptian Pounds (EGP)",
                f"Exchange rate: 1 EGP = {egp_per_usd_inv:.4f} USD "
                f"(from {rate_source}, {rate_date.isoformat()})",
                f"USD value calculated as: EGP {primary_value_egp:,.0f} "
                f"÷ {exchange_rate:.4f} = USD {primary_value_usd:,.0f}",
                "Exchange rate assumed constant for valuation purposes only",
                "Actual exchange rates may differ at time of transaction",
            ],
            certification_statement=(
                f"This valuation is expressed in both Egyptian Pounds "
                f"(EGP {primary_value_egp:,.0f}) and US Dollars "
                f"(USD {primary_value_usd:,.0f}). "
                f"The USD conversion is based on an exchange rate of "
                f"1 EGP = {egp_per_usd_inv:.4f} USD obtained from {rate_source} "
                f"on {rate_date.isoformat()}. "
                f"This valuation does not represent an opinion of future exchange rates."
            ),
        )
        self.disclosures["cross_border_usd"] = disclosure
        return disclosure

    # ── Multi-currency ────────────────────────────────────────────────────────

    def multi_currency(
        self,
        primary_value_egp: float,
        usd_rate: float,                    # EGP per 1 USD
        eur_rate: float,                    # EGP per 1 EUR
        rate_source: str = "Central Bank of Egypt",
        rate_date: Optional[date] = None,
    ) -> CrossBorderDisclosure:
        """Build disclosure for multi-currency valuation (EGP, USD, EUR)."""
        if rate_date is None:
            rate_date = date.today()

        primary_value_usd = primary_value_egp / usd_rate
        primary_value_eur = primary_value_egp / eur_rate
        egp_per_usd_inv   = 1 / usd_rate
        egp_per_eur_inv   = 1 / eur_rate

        disclosure = CrossBorderDisclosure(
            subject_property_currency=Currency.EGP,
            reporting_currency=Currency.EGP,
            exchange_rate_assumption=ExchangeRateAssumption(
                from_currency=Currency.EGP,
                to_currency=Currency.USD,
                rate=egp_per_usd_inv,
                effective_date=rate_date,
                source=rate_source,
                currency_risk_disclosure=(
                    "Multi-currency valuation with exchange rate risk disclosure"
                ),
            ),
            property_location_country="Egypt",
            valuation_purpose_country="International",
            primary_value_egp=primary_value_egp,
            primary_value_usd=primary_value_usd,
            primary_value_eur=primary_value_eur,
            currency_risk_statement=(
                f"Property valued in Egyptian Pounds and converted to USD and EUR for "
                f"international clients. "
                f"Exchange rate risk applies to all conversions. "
                f"USD and EUR values are estimates only and subject to exchange rate "
                f"fluctuation."
            ),
            reporting_assumptions=[
                f"Primary valuation: EGP {primary_value_egp:,.0f}",
                f"USD conversion (1 EGP = {egp_per_usd_inv:.4f} USD): "
                f"USD {primary_value_usd:,.0f}",
                f"EUR conversion (1 EGP = {egp_per_eur_inv:.4f} EUR): "
                f"EUR {primary_value_eur:,.0f}",
                f"Exchange rates from {rate_source}, {rate_date.isoformat()}",
                "Exchange rates assumed constant for valuation purposes only",
                "Actual transaction values may differ significantly",
            ],
            certification_statement=(
                f"This valuation is expressed in Egyptian Pounds, US Dollars, and Euros. "
                f"Primary valuation: EGP {primary_value_egp:,.0f}. "
                f"Conversions: USD {primary_value_usd:,.0f} "
                f"(at 1 EGP = {egp_per_usd_inv:.4f} USD) and "
                f"EUR {primary_value_eur:,.0f} "
                f"(at 1 EGP = {egp_per_eur_inv:.4f} EUR). "
                f"All exchange rates obtained from {rate_source} on {rate_date.isoformat()}."
            ),
        )
        self.disclosures["multi_currency"] = disclosure
        return disclosure
