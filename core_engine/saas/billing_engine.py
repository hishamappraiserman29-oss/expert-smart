"""
billing_engine.py — Usage metering, invoice generation, and payment tracking.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional


class UsageMetric(Enum):
    VALUATION = "valuation"
    API_CALL = "api_call"
    REPORT = "report"
    STORAGE_GB = "storage_gb"
    USER_SEAT = "user_seat"


# Price per unit (USD) per metric per tier
_UNIT_PRICES: Dict[str, Dict[UsageMetric, float]] = {
    "free":         {m: 0.0 for m in UsageMetric},
    "starter":      {
        UsageMetric.VALUATION:  0.50,
        UsageMetric.API_CALL:   0.001,
        UsageMetric.REPORT:     1.00,
        UsageMetric.STORAGE_GB: 0.10,
        UsageMetric.USER_SEAT:  10.00,
    },
    "professional": {
        UsageMetric.VALUATION:  0.30,
        UsageMetric.API_CALL:   0.0005,
        UsageMetric.REPORT:     0.75,
        UsageMetric.STORAGE_GB: 0.08,
        UsageMetric.USER_SEAT:  20.00,
    },
    "enterprise":   {
        UsageMetric.VALUATION:  0.10,
        UsageMetric.API_CALL:   0.0001,
        UsageMetric.REPORT:     0.25,
        UsageMetric.STORAGE_GB: 0.05,
        UsageMetric.USER_SEAT:  50.00,
    },
}

_BASE_PRICES: Dict[str, float] = {
    "free": 0.0,
    "starter": 49.0,
    "professional": 199.0,
    "enterprise": 999.0,
}


@dataclass
class UsageRecord:
    record_id: str
    tenant_id: str
    metric: UsageMetric
    quantity: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "tenant_id": self.tenant_id,
            "metric": self.metric.value,
            "quantity": self.quantity,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class InvoiceLineItem:
    metric: UsageMetric
    quantity: float
    unit_price: float

    @property
    def total(self) -> float:
        return round(self.quantity * self.unit_price, 4)

    def to_dict(self) -> dict:
        return {
            "metric": self.metric.value,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total": self.total,
        }


@dataclass
class Invoice:
    invoice_id: str
    tenant_id: str
    period_start: datetime
    period_end: datetime
    tier: str
    base_price: float
    line_items: List[InvoiceLineItem] = field(default_factory=list)
    paid: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def usage_total(self) -> float:
        return round(sum(item.total for item in self.line_items), 2)

    @property
    def total_amount(self) -> float:
        return round(self.base_price + self.usage_total, 2)

    def to_dict(self) -> dict:
        return {
            "invoice_id": self.invoice_id,
            "tenant_id": self.tenant_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "tier": self.tier,
            "base_price": self.base_price,
            "line_items": [li.to_dict() for li in self.line_items],
            "usage_total": self.usage_total,
            "total_amount": self.total_amount,
            "paid": self.paid,
            "created_at": self.created_at.isoformat(),
        }


class BillingEngine:
    """Tracks usage and generates invoices per tenant."""

    def __init__(self) -> None:
        self._usage: Dict[str, List[UsageRecord]] = {}  # tenant_id -> records
        self._invoices: Dict[str, List[Invoice]] = {}   # tenant_id -> invoices
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Usage recording
    # ------------------------------------------------------------------

    def record_usage(
        self,
        tenant_id: str,
        metric: UsageMetric,
        quantity: float = 1.0,
        metadata: Optional[Dict] = None,
    ) -> UsageRecord:
        record = UsageRecord(
            record_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            metric=metric,
            quantity=quantity,
            metadata=metadata or {},
        )
        with self._lock:
            self._usage.setdefault(tenant_id, []).append(record)
        return record

    def get_usage(
        self,
        tenant_id: str,
        metric: Optional[UsageMetric] = None,
        since: Optional[datetime] = None,
    ) -> List[UsageRecord]:
        with self._lock:
            records = list(self._usage.get(tenant_id, []))
        if metric is not None:
            records = [r for r in records if r.metric == metric]
        if since is not None:
            records = [r for r in records if r.timestamp >= since]
        return records

    def get_usage_summary(self, tenant_id: str, since: Optional[datetime] = None) -> Dict[str, float]:
        records = self.get_usage(tenant_id, since=since)
        summary: Dict[str, float] = {}
        for r in records:
            key = r.metric.value
            summary[key] = summary.get(key, 0.0) + r.quantity
        return summary

    # ------------------------------------------------------------------
    # Invoice generation
    # ------------------------------------------------------------------

    def generate_invoice(
        self,
        tenant_id: str,
        tier: str,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> Invoice:
        now = datetime.utcnow()
        if period_end is None:
            period_end = now
        if period_start is None:
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        tier_key = tier.lower()
        base_price = _BASE_PRICES.get(tier_key, 0.0)
        prices = _UNIT_PRICES.get(tier_key, {})

        # Aggregate usage in period
        records = self.get_usage(tenant_id, since=period_start)
        records = [r for r in records if r.timestamp <= period_end]

        aggregated: Dict[UsageMetric, float] = {}
        for r in records:
            aggregated[r.metric] = aggregated.get(r.metric, 0.0) + r.quantity

        line_items = [
            InvoiceLineItem(
                metric=metric,
                quantity=qty,
                unit_price=prices.get(metric, 0.0),
            )
            for metric, qty in aggregated.items()
        ]

        invoice = Invoice(
            invoice_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            tier=tier_key,
            base_price=base_price,
            line_items=line_items,
        )
        with self._lock:
            self._invoices.setdefault(tenant_id, []).append(invoice)
        return invoice

    def mark_paid(self, invoice_id: str) -> bool:
        with self._lock:
            for invoices in self._invoices.values():
                for inv in invoices:
                    if inv.invoice_id == invoice_id:
                        inv.paid = True
                        return True
        return False

    def get_invoices(self, tenant_id: str) -> List[Invoice]:
        with self._lock:
            return list(self._invoices.get(tenant_id, []))

    def get_outstanding_balance(self, tenant_id: str) -> float:
        with self._lock:
            invoices = self._invoices.get(tenant_id, [])
            return round(sum(inv.total_amount for inv in invoices if not inv.paid), 2)
