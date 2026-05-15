"""
data_mapper.py — Flexible Data Transformation (Phase 40)

Maps records between internal and external system formats.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FieldMapping:
    """Maps a single field from source to destination with optional transform."""

    def __init__(
        self,
        source_field: str,
        dest_field: str,
        transform: Optional[Callable[[Any], Any]] = None,
        required: bool = False,
    ) -> None:
        self.source_field = source_field
        self.dest_field = dest_field
        self.transform = transform
        self.required = required

    def apply(self, source_data: Dict[str, Any]) -> Tuple[Optional[str], Any]:
        if self.source_field not in source_data:
            if self.required:
                raise ValueError(f"Required field missing: {self.source_field}")
            return None, None
        value = source_data[self.source_field]
        if self.transform is not None:
            try:
                value = self.transform(value)
            except Exception as exc:
                logger.error("Transform error on field %s: %s", self.source_field, exc)
                raise
        return self.dest_field, value


class DataMapper:
    """Map data records between different schema formats."""

    def __init__(self) -> None:
        self.mappings: Dict[str, Dict[str, FieldMapping]] = {
            "property_to_bank": {
                "property_id": FieldMapping("property_id", "collateral_id"),
                "area": FieldMapping("area_sqm", "area_sqm"),
                "price": FieldMapping(
                    "price", "appraised_value", lambda x: float(x) if x is not None else 0.0
                ),
                "type": FieldMapping("property_type", "collateral_type"),
                "location": FieldMapping("location", "property_address"),
                "condition": FieldMapping("condition", "condition"),
            },
            "bank_to_property": {
                "loan_amount": FieldMapping(
                    "loan_amount", "loan_amount", lambda x: float(x) if x is not None else 0.0
                ),
                "borrower": FieldMapping("borrower_id", "borrower_id"),
                "property": FieldMapping("property_id", "property_id"),
                "purpose": FieldMapping("purpose", "loan_purpose"),
            },
            "valuation_to_government": {
                "value": FieldMapping("final_value", "appraised_value"),
                "date": FieldMapping(
                    "valuation_date",
                    "valuation_date",
                    lambda x: datetime.fromisoformat(x) if isinstance(x, str) else x,
                ),
                "method": FieldMapping("primary_method", "valuation_method"),
                "property": FieldMapping("property_id", "property_id"),
            },
            "valuation_to_crm": {
                "id": FieldMapping("valuation_id", "opportunity_id"),
                "value": FieldMapping("final_value", "deal_value"),
                "status": FieldMapping("status", "stage"),
            },
            "mls_to_property": {
                "listing_id": FieldMapping("listing_id", "external_id"),
                "price": FieldMapping(
                    "list_price", "price", lambda x: float(x) if x is not None else 0.0
                ),
                "area": FieldMapping("sqft", "area_sqm", lambda x: float(x) * 0.0929 if x else 0.0),
                "type": FieldMapping("property_type", "property_type"),
            },
        }
        logger.info("DataMapper initialized with %d mappings", len(self.mappings))

    def map_data(self, source_data: Dict[str, Any], mapping_name: str) -> Dict[str, Any]:
        if mapping_name not in self.mappings:
            raise ValueError(f"Mapping not found: {mapping_name}")
        result: Dict[str, Any] = {}
        for _field_key, field_mapping in self.mappings[mapping_name].items():
            try:
                dest_field, value = field_mapping.apply(source_data)
                if dest_field is not None and value is not None:
                    result[dest_field] = value
            except ValueError:
                if field_mapping.required:
                    raise
                logger.warning("Optional field skipped: %s", field_mapping.source_field)
        return result

    def register_mapping(self, mapping_name: str, mappings: Dict[str, FieldMapping]) -> None:
        self.mappings[mapping_name] = mappings
        logger.info("Mapping registered: %s (%d fields)", mapping_name, len(mappings))

    def validate_mapping(
        self, source_data: Dict[str, Any], mapping_name: str
    ) -> Tuple[bool, str]:
        if mapping_name not in self.mappings:
            return False, f"Mapping not found: {mapping_name}"
        errors: List[str] = []
        for field_mapping in self.mappings[mapping_name].values():
            if field_mapping.required and field_mapping.source_field not in source_data:
                errors.append(f"Required field missing: {field_mapping.source_field}")
        if errors:
            return False, "; ".join(errors)
        return True, "Validation passed"

    def list_mappings(self) -> List[str]:
        return list(self.mappings.keys())


data_mapper = DataMapper()
