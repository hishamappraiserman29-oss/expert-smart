"""
evaluate_avm_model.py — Evaluate a saved AVM model on new data.

Usage:
  python scripts/evaluate_avm_model.py --model models/avm_model.pkl --data data/test.csv
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s — %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)


def evaluate_saved_model(model_path: str, data_source: str) -> dict:
    """Load a saved model and evaluate it against *data_source*."""
    import joblib
    from ml.data_processor import DataProcessor
    from ml.feature_engineer import FeatureEngineer
    from ml.model_validator import ModelValidator

    logger.info("Loading model from %s", model_path)
    model = joblib.load(model_path)

    logger.info("Loading evaluation data from %s", data_source)
    processor = DataProcessor()
    processor.load_data(data_source)
    processor.clean_data()

    engineer = FeatureEngineer()
    X_raw = engineer.extract_features(processor.processed_data)
    y     = processor.processed_data["primary_value"].values

    available = [f for f in engineer.feature_names if f in X_raw.columns]
    X         = X_raw[available].values.astype(float)

    y_pred   = model.predict(X)
    metrics  = ModelValidator.evaluate(y, y_pred)

    logger.info(ModelValidator.generate_report(metrics))

    subgroup = ModelValidator.validate_by_subgroup(
        processor.processed_data.reset_index(drop=True),
        y, y_pred, "property_type",
    )

    output = {"metrics": metrics, "subgroup_metrics": subgroup}
    out_path = Path(model_path).with_suffix(".eval.json")
    out_path.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    logger.info("Evaluation results saved to %s", out_path)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate AVM model")
    parser.add_argument("--model", required=True, help="Path to saved model .pkl")
    parser.add_argument("--data",  required=True, help="Path to evaluation data (CSV/JSON)")
    args = parser.parse_args()

    result = evaluate_saved_model(args.model, args.data)
    print(f"\nTest R²  : {result['metrics']['r2']:.4f}")
    print(f"MAE      : EGP {result['metrics']['mae']:,.0f}")
    print(f"Within 10%: {result['metrics']['accuracy_within_ranges']['10_percent']:.1f}%")
