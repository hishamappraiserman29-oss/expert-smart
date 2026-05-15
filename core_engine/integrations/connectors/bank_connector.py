"""
bank_connector.py — Bank System Connector (Phase 40)

Integration with CBE and commercial bank APIs.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from ..connector_base import BaseConnector, ConnectorConfig, SyncDirection

logger = logging.getLogger(__name__)


class BankConnector(BaseConnector):
    """Connector for banking systems (mortgages, collateral, LTV)."""

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)
        self.bank_code: Optional[str] = config.custom_params.get("bank_code")
        self.branch_id: Optional[str] = config.custom_params.get("branch_id")
        logger.info("BankConnector ready: %s (bank_code=%s)", config.name, self.bank_code)

    def validate_connection(self) -> bool:
        if self.session is None:
            return False
        try:
            response = self.session.get(f"{self.config.endpoint_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as exc:
            logger.error("Bank connection validation failed: %s", exc)
            return False

    def pull_data(self) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        if self.session is None:
            return [], "requests library not available"
        try:
            response = self.session.get(
                f"{self.config.endpoint_url}/mortgages",
                params={"bank_code": self.bank_code, "status": "active"},
                timeout=30,
            )
            if response.status_code != 200:
                return [], f"Bank API error: {response.status_code}"
            mortgages = response.json().get("data", [])
            logger.info("Pulled %d mortgages from bank", len(mortgages))
            return mortgages, None
        except Exception as exc:
            logger.error("pull_data error: %s", exc)
            return [], str(exc)

    def push_data(self, data: List[Dict[str, Any]]) -> Tuple[int, int]:
        if self.session is None:
            return 0, len(data)
        synced = failed = 0
        for item in data:
            try:
                response = self.session.post(
                    f"{self.config.endpoint_url}/collateral/{item['collateral_id']}/valuation",
                    json=self.transform_outgoing(item),
                    timeout=10,
                )
                if response.status_code == 200:
                    synced += 1
                else:
                    failed += 1
            except Exception as exc:
                logger.error("push_data error for %s: %s", item.get("collateral_id"), exc)
                failed += 1
        return synced, failed

    def transform_incoming(self, external_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "external_id": external_data.get("mortgage_id"),
            "collateral_id": external_data.get("property_id"),
            "loan_amount": external_data.get("loan_amount"),
            "loan_purpose": external_data.get("purpose"),
            "borrower_id": external_data.get("borrower_id"),
            "property_location": external_data.get("property_location"),
            "property_type": external_data.get("property_type"),
            "area_sqm": external_data.get("area_sqm"),
            "status": "pending_valuation",
            "created_at": external_data.get("created_date"),
        }

    def transform_outgoing(self, internal_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "collateral_id": internal_data.get("collateral_id"),
            "valuation_id": internal_data.get("valuation_id"),
            "appraised_value": internal_data.get("final_value"),
            "collateral_type": internal_data.get("property_type"),
            "condition": internal_data.get("condition"),
            "ltv": internal_data.get("ltv"),
            "valuation_methods": internal_data.get("valuation_methods"),
            "valuation_date": internal_data.get("valuation_date"),
            "expires_date": internal_data.get("expires_date"),
        }
