"""
train_avm_model.py — End-to-end AVM training pipeline.

Usage:
  python scripts/train_avm_model.py --data path/to/data.csv --output models/
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)
logger = logging.getLogger(__name__)


def train_avm_pipeline(data_source: str, output_dir: str = "models") -> dict:
    """Run the full AVM training pipeline and return result paths + metrics."""
    from ml.data_processor import DataProcessor
    from ml.feature_engineer import FeatureEngineer
    from ml.model_trainer import ModelTrainer
    from ml.model_validator import ModelValidator
    from ml.avm_predictor import AVMPredictor

    logger.info("=" * 60)
    logger.info("STARTING AVM TRAINING PIPELINE")
    logger.info("=" * 60)

    # ── Step 1: Data ──────────────────────────────────────────────────
    logger.info("STEP 1: DATA LOADING & CLEANING")
    processor = DataProcessor()
    processor.load_data(data_source)
    processor.clean_data()
    stats = processor.get_statistics()
    logger.info("Records: %d | Price range: EGP %.0f – %.0f",
                stats["total_records"],
                stats["primary_value"]["min"],
                stats["primary_value"]["max"])

    # ── Step 2: Features ──────────────────────────────────────────────
    logger.info("STEP 2: FEATURE ENGINEERING")
    engineer = FeatureEngineer()
    train_df, test_df = processor.split_by_time(test_size=0.2)

    X_train_raw = engineer.extract_features(train_df)
    X_test_raw  = engineer.extract_features(test_df)

    y_train = train_df["primary_value"].values
    y_test  = test_df["primary_value"].values

    available_train = [f for f in engineer.feature_names if f in X_train_raw.columns]
    available_test  = [f for f in engineer.feature_names if f in X_test_raw.columns]

    X_train = X_train_raw[available_train].values.astype(float)
    X_test  = X_test_raw[available_test].values.astype(float)

    logger.info("Features: %d | Train: %d | Test: %d",
                len(available_train), len(X_train), len(X_test))

    # ── Step 3: Training ──────────────────────────────────────────────
    logger.info("STEP 3: MODEL TRAINING")
    trainer = ModelTrainer()
    training_results = trainer.train_ensemble(X_train, y_train)

    for algo, res in training_results.items():
        if not res.get("skipped"):
            logger.info("  %-22s CV R² = %.4f ± %.4f", algo, res["cv_mean"], res["cv_std"])

    # ── Step 4: Evaluation ────────────────────────────────────────────
    logger.info("STEP 4: MODEL EVALUATION")
    y_train_pred = trainer.best_model.predict(X_train)
    y_test_pred  = trainer.best_model.predict(X_test)

    train_metrics = ModelValidator.evaluate(y_train, y_train_pred)
    test_metrics  = ModelValidator.evaluate(y_test, y_test_pred)
    ModelValidator.check_overfitting(train_metrics["r2"], test_metrics["r2"])

    logger.info("TEST SET:\n%s", ModelValidator.generate_report(test_metrics))

    # ── Step 5: Subgroup validation ───────────────────────────────────
    logger.info("STEP 5: VALIDATION BY PROPERTY TYPE")
    subgroup = ModelValidator.validate_by_subgroup(
        test_df.reset_index(drop=True),
        y_test,
        y_test_pred,
        "property_type",
    )
    for pt, m in subgroup.items():
        logger.info("  %-15s R²=%.4f  MAE=EGP %.0f", pt, m["r2"], m["mae"])

    # ── Step 6: Save ──────────────────────────────────────────────────
    logger.info("STEP 6: SAVING MODELS")
    os.makedirs(output_dir, exist_ok=True)
    model_path   = os.path.join(output_dir, "avm_model.pkl")
    metrics_path = os.path.join(output_dir, "avm_metrics.json")

    trainer.save_model(model_path)
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(
            {"train_metrics": train_metrics, "test_metrics": test_metrics,
             "subgroup_metrics": subgroup, "data_stats": stats},
            f, indent=2, default=str,
        )

    # ── Step 7: Sample prediction ────────────────────────────────────
    logger.info("STEP 7: SAMPLE PREDICTION")
    predictor = AVMPredictor(trainer.best_model, engineer)
    sample = predictor.predict(area_sqm=150, location="Cairo", property_type="residential")
    if sample.get("predicted_value"):
        logger.info(
            "150 sqm / Cairo / residential → EGP %.0f (CI: %.0f – %.0f)",
            sample["predicted_value"],
            sample["confidence_interval"]["lower_5"],
            sample["confidence_interval"]["upper_95"],
        )

    logger.info("=" * 60)
    logger.info("AVM TRAINING PIPELINE COMPLETE")
    logger.info("  Best algorithm : %s", trainer.best_algorithm)
    logger.info("  Test R²        : %.4f", test_metrics["r2"])
    logger.info("  Within 10%%     : %.1f%%", test_metrics["accuracy_within_ranges"]["10_percent"])
    logger.info("=" * 60)

    return {
        "model_path": model_path,
        "metrics_path": metrics_path,
        "test_metrics": test_metrics,
        "best_algorithm": trainer.best_algorithm,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train AVM model")
    parser.add_argument("--data",   required=True, help="Path to training data (CSV/JSON)")
    parser.add_argument("--output", default="models", help="Output directory for model artefacts")
    args = parser.parse_args()

    result = train_avm_pipeline(args.data, args.output)
    print(f"\nModel : {result['model_path']}")
    print(f"Metrics: {result['metrics_path']}")
    print(f"Test R²: {result['test_metrics']['r2']:.4f}")
