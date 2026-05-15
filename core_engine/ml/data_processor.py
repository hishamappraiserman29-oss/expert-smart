"""
data_processor.py — Data loading, cleaning, and train/test splitting for AVM.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_CRITICAL_FIELDS = ["area_sqm", "location", "property_type", "primary_value"]


class DataProcessor:
    """Load, validate, and prepare data for ML training."""

    def __init__(self) -> None:
        self.raw_data: Optional[pd.DataFrame] = None
        self.processed_data: Optional[pd.DataFrame] = None
        self.statistics: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_data(self, data_source: str) -> pd.DataFrame:
        """Load data from CSV, JSON, or a SQLAlchemy connection string."""
        try:
            if data_source.endswith(".csv"):
                self.raw_data = pd.read_csv(data_source)
            elif data_source.endswith(".json"):
                self.raw_data = pd.read_json(data_source)
            else:
                import sqlalchemy  # type: ignore
                engine = sqlalchemy.create_engine(data_source)
                self.raw_data = pd.read_sql(
                    "SELECT * FROM valuations WHERE status='completed'",
                    engine,
                )
            logger.info("Loaded %d records from %s", len(self.raw_data), data_source)
            return self.raw_data
        except Exception as exc:
            logger.error("Error loading data: %s", exc)
            raise

    def load_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Accept an already-built DataFrame directly (used in tests/pipelines)."""
        self.raw_data = df.copy()
        return self.raw_data

    # ------------------------------------------------------------------
    # Cleaning
    # ------------------------------------------------------------------

    def clean_data(self) -> pd.DataFrame:
        """Remove duplicates, bad values, and outliers; cast types."""
        if self.raw_data is None:
            raise ValueError("No data loaded — call load_data() or load_dataframe() first")

        df = self.raw_data.copy()
        initial = len(df)

        df = df.drop_duplicates()
        logger.info("Removed %d duplicate records", initial - len(df))

        df = df.dropna(subset=_CRITICAL_FIELDS)
        logger.info("Removed %d records with missing critical fields", initial - len(df))

        # Outlier bounds
        df = df[(df["area_sqm"] >= 20) & (df["area_sqm"] <= 10_000)]
        df = df[(df["primary_value"] >= 10_000) & (df["primary_value"] <= 100_000_000)]

        # Type coercion
        df["area_sqm"] = pd.to_numeric(df["area_sqm"], errors="coerce")
        df["primary_value"] = pd.to_numeric(df["primary_value"], errors="coerce")
        if "created_at" in df.columns:
            df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

        df = df.dropna(subset=_CRITICAL_FIELDS)

        self.processed_data = df
        logger.info("Cleaned data: %d records remaining", len(df))
        return df

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_statistics(self) -> Dict[str, Any]:
        """Return descriptive stats for the processed dataset."""
        if self.processed_data is None:
            return {}

        df = self.processed_data
        price_per_sqm = df["primary_value"] / df["area_sqm"]

        stats: Dict[str, Any] = {
            "total_records": len(df),
            "area_sqm": {
                "min": float(df["area_sqm"].min()),
                "max": float(df["area_sqm"].max()),
                "mean": float(df["area_sqm"].mean()),
                "median": float(df["area_sqm"].median()),
                "std": float(df["area_sqm"].std()),
            },
            "primary_value": {
                "min": float(df["primary_value"].min()),
                "max": float(df["primary_value"].max()),
                "mean": float(df["primary_value"].mean()),
                "median": float(df["primary_value"].median()),
                "std": float(df["primary_value"].std()),
            },
            "property_types": df["property_type"].value_counts().to_dict(),
            "locations": int(df["location"].nunique()),
            "price_per_sqm": {
                "min": float(price_per_sqm.min()),
                "max": float(price_per_sqm.max()),
                "mean": float(price_per_sqm.mean()),
            },
        }

        if "created_at" in df.columns and df["created_at"].notna().any():
            stats["date_range"] = {
                "start": str(df["created_at"].min()),
                "end": str(df["created_at"].max()),
            }

        self.statistics = stats
        return stats

    def get_sample_data(self, n: int = 100) -> pd.DataFrame:
        """Return a random sample for exploration."""
        if self.processed_data is None:
            return pd.DataFrame()
        return self.processed_data.sample(n=min(n, len(self.processed_data)), random_state=42)

    # ------------------------------------------------------------------
    # Splitting
    # ------------------------------------------------------------------

    def split_train_test(
        self,
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Random train/test split."""
        if self.processed_data is None:
            raise ValueError("No processed data — call clean_data() first")

        from sklearn.model_selection import train_test_split  # type: ignore

        train, test = train_test_split(
            self.processed_data,
            test_size=test_size,
            random_state=random_state,
        )
        logger.info("Split: %d train / %d test", len(train), len(test))
        return train, test

    def split_by_time(
        self,
        test_size: float = 0.2,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Temporal split — older records for training, recent for test."""
        if self.processed_data is None:
            raise ValueError("No processed data — call clean_data() first")

        sort_col = "created_at" if "created_at" in self.processed_data.columns else None
        df_sorted = (
            self.processed_data.sort_values(sort_col)
            if sort_col
            else self.processed_data
        )

        split_point = int(len(df_sorted) * (1 - test_size))
        train = df_sorted.iloc[:split_point]
        test = df_sorted.iloc[split_point:]

        logger.info("Time-split: %d train / %d test", len(train), len(test))
        return train, test
