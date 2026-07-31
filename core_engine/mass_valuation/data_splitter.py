"""
data_splitter.py — P6 train/validation splitting for mass valuation.
D-06: temporal split — validation period starts strictly after a date cutoff.
D-07: geographic split — held-out cities excluded from training.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Tuple


def temporal_split(
    records: List[Dict[str, Any]],
    cutoff_date: str,
) -> Tuple[List[Dict], List[Dict]]:
    """
    D-06: Partition records into train (on/before cutoff) and validation (after).

    Records whose transaction_date is absent or unparseable go to training.
    cutoff_date must be ISO-8601: "YYYY-MM-DD".
    Returns (train_records, validation_records).
    """
    cutoff = date.fromisoformat(cutoff_date)
    train:      List[Dict] = []
    validation: List[Dict] = []

    for rec in records:
        tx_str = rec.get("transaction_date")
        placed = False
        if tx_str:
            try:
                tx_date = date.fromisoformat(str(tx_str)[:10])
                if tx_date > cutoff:
                    validation.append(rec)
                    placed = True
            except (ValueError, TypeError):
                pass
        if not placed:
            train.append(rec)

    return train, validation


def geographic_split(
    records: List[Dict[str, Any]],
    holdout_cities: List[str],
) -> Tuple[List[Dict], List[Dict]]:
    """
    D-07: Partition records into train (excluding holdout_cities) and holdout.

    Matching is case-insensitive against the 'city' field.
    Returns (train_records, holdout_records).
    """
    holdout_set = {c.lower() for c in holdout_cities}
    train:   List[Dict] = []
    holdout: List[Dict] = []

    for rec in records:
        city = str(rec.get("city", "")).lower()
        if city in holdout_set:
            holdout.append(rec)
        else:
            train.append(rec)

    return train, holdout
