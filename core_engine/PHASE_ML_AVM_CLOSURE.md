# Phase ML/AVM — Closure Document

## Summary
Automated Valuation Model (AVM) training pipeline implemented end-to-end.

## Files Created

| File | Purpose |
|------|---------|
| `ml/__init__.py` | Package exports |
| `ml/data_processor.py` | Load, clean, split historical valuation data |
| `ml/feature_engineer.py` | Price-per-sqm, size flags, location/type target encoding, time features, one-hot encoding |
| `ml/model_trainer.py` | Random Forest, Gradient Boosting, XGBoost (optional) with CV + ensemble selection |
| `ml/model_validator.py` | RMSE, MAE, MAPE, R², accuracy-within-ranges, subgroup validation, overfitting check |
| `ml/avm_predictor.py` | Single/batch prediction with 90% confidence intervals, explainability |
| `ml/model_registry.py` | Versioned model storage with activation/deactivation lifecycle |
| `scripts/train_avm_model.py` | 7-step CLI training pipeline |
| `scripts/evaluate_avm_model.py` | Evaluate saved model on new data, write `.eval.json` |
| `tests/test_ml_avm.py` | 52 tests (A01–F06) |

## bridge_api.py Endpoints Added

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/valuation/avm` | POST | Single property AVM prediction |
| `/api/valuation/avm/batch` | POST | Batch AVM prediction (up to 500 properties) |
| `/api/avm/info` | GET | Active model info and registry stats |

All endpoints guarded by `_ML_OK` flag; degrade gracefully when module unavailable.

## Key Design Decisions

- **XGBoost optional**: `try/except ImportError` with `_XGBOOST_OK` flag; returns `{"skipped": True}` without raising
- **Inference feature alignment**: `FeatureEngineer` detects "fitted" state via `categorical_features`; subsequent calls (test/inference) use stored group stats and align one-hot columns to training schema
- **Confidence intervals**: Per-tree percentile 5/95 from `model.estimators_`; fallback ±10% if fewer than 2 trees

## Test Results
- **52/52 tests pass** (A01–A10 DataProcessor, B01–B09 FeatureEngineer, C01–C09 ModelTrainer, D01–D09 ModelValidator, E01–E09 AVMPredictor, F01–F06 ModelRegistry)
- **602/602 full suite** — zero regressions

## Bug Fixed During Testing
`FeatureEngineer.extract_features()` overwrote `categorical_features` on every call, causing feature-count mismatch at inference (14 features vs 16 expected). Fixed by detecting fitted state at call start and aligning one-hot columns to training schema during inference.
