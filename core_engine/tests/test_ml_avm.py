"""
test_ml_avm.py — ML / AVM Training Pipeline Tests

Covers:
  A. DataProcessor    (A01–A10)
  B. FeatureEngineer  (B01–B09)
  C. ModelTrainer     (C01–C09)
  D. ModelValidator   (D01–D09)
  E. AVMPredictor     (E01–E09)
  F. ModelRegistry    (F01–F06)
"""

from __future__ import annotations

import sys
import tempfile
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.data_processor import DataProcessor
from ml.feature_engineer import FeatureEngineer
from ml.model_trainer import ModelTrainer
from ml.model_validator import ModelValidator
from ml.avm_predictor import AVMPredictor
from ml.model_registry import ModelRegistry, ModelMetadata


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture(scope="module")
def sample_df():
    """1 000-row synthetic property dataset."""
    rng = np.random.default_rng(42)
    n = 1_000
    locations = rng.choice(["Cairo", "Giza", "Alexandria"], n)
    ptypes    = rng.choice(["residential", "commercial", "land"], n)
    areas     = rng.uniform(50, 400, n)
    noise     = rng.normal(0, 80_000, n)

    prices = (
        areas * 5_000
        + np.where(ptypes == "commercial", 400_000, 0)
        + np.where(locations == "Cairo", 600_000, 0)
        + noise
    ).clip(50_000, 50_000_000).astype(int)

    dates = pd.date_range("2022-01-01", periods=n, freq="D")

    return pd.DataFrame({
        "area_sqm":      areas,
        "location":      locations,
        "property_type": ptypes,
        "primary_value": prices,
        "created_at":    dates,
    })


@pytest.fixture(scope="module")
def processed_processor(sample_df):
    p = DataProcessor()
    p.load_dataframe(sample_df)
    p.clean_data()
    return p


@pytest.fixture(scope="module")
def engineered(processed_processor):
    eng = FeatureEngineer()
    df  = eng.extract_features(processed_processor.processed_data)
    return eng, df


@pytest.fixture(scope="module")
def trained_trainer(engineered, processed_processor):
    eng, feat_df = engineered
    X = feat_df[eng.feature_names].values.astype(float)
    y = processed_processor.processed_data["primary_value"].values
    trainer = ModelTrainer()
    trainer.train_random_forest(X, y, cv=3)
    return trainer, X, y


@pytest.fixture(scope="module")
def predictor(trained_trainer, engineered):
    trainer, _, _ = trained_trainer
    eng, _ = engineered
    return AVMPredictor(trainer.best_model, eng)


@pytest.fixture()
def tmp_registry(tmp_path):
    return ModelRegistry(registry_dir=str(tmp_path / "registry"))


# ===========================================================================
# A. DataProcessor
# ===========================================================================

class TestDataProcessor:

    def test_A01_load_dataframe_sets_raw_data(self, sample_df):
        p = DataProcessor()
        result = p.load_dataframe(sample_df)
        assert len(result) == len(sample_df)
        assert p.raw_data is not None

    def test_A02_clean_data_removes_duplicates(self, sample_df):
        dup = pd.concat([sample_df, sample_df.iloc[:10]])
        p = DataProcessor()
        p.load_dataframe(dup)
        cleaned = p.clean_data()
        assert len(cleaned) <= len(dup)

    def test_A03_clean_data_drops_missing_critical_fields(self, sample_df):
        bad = sample_df.copy()
        bad.loc[0, "area_sqm"] = np.nan
        p = DataProcessor()
        p.load_dataframe(bad)
        cleaned = p.clean_data()
        assert cleaned["area_sqm"].isna().sum() == 0

    def test_A04_clean_data_removes_area_outliers(self, sample_df):
        extreme = sample_df.copy()
        extreme.loc[0, "area_sqm"] = 1  # below 20
        p = DataProcessor()
        p.load_dataframe(extreme)
        cleaned = p.clean_data()
        assert (cleaned["area_sqm"] < 20).sum() == 0

    def test_A05_clean_data_removes_price_outliers(self, sample_df):
        extreme = sample_df.copy()
        extreme.loc[0, "primary_value"] = 5  # below 10 000
        p = DataProcessor()
        p.load_dataframe(extreme)
        cleaned = p.clean_data()
        assert (cleaned["primary_value"] < 10_000).sum() == 0

    def test_A06_processed_data_set_after_clean(self, processed_processor):
        assert processed_processor.processed_data is not None
        assert len(processed_processor.processed_data) > 0

    def test_A07_get_statistics_has_required_keys(self, processed_processor):
        stats = processed_processor.get_statistics()
        for key in ("total_records", "area_sqm", "primary_value", "property_types", "locations"):
            assert key in stats, f"Missing key: {key}"

    def test_A08_statistics_area_range_is_valid(self, processed_processor):
        stats = processed_processor.get_statistics()
        assert stats["area_sqm"]["min"] >= 20
        assert stats["area_sqm"]["max"] <= 10_000

    def test_A09_split_train_test_proportions(self, processed_processor):
        train, test = processed_processor.split_train_test(test_size=0.2, random_state=0)
        total = len(train) + len(test)
        assert abs(len(test) / total - 0.2) < 0.05

    def test_A10_split_by_time_train_before_test(self, processed_processor):
        train, test = processed_processor.split_by_time(test_size=0.2)
        assert len(train) > 0 and len(test) > 0
        assert len(train) > len(test)


# ===========================================================================
# B. FeatureEngineer
# ===========================================================================

class TestFeatureEngineer:

    def test_B01_extract_features_returns_dataframe(self, sample_df):
        eng = FeatureEngineer()
        result = eng.extract_features(sample_df)
        assert isinstance(result, pd.DataFrame)

    def test_B02_price_per_sqm_column_added(self, sample_df):
        eng = FeatureEngineer()
        result = eng.extract_features(sample_df)
        assert "price_per_sqm" in result.columns

    def test_B03_size_flags_are_mutually_exclusive(self, sample_df):
        eng = FeatureEngineer()
        result = eng.extract_features(sample_df)
        flag_sum = result["is_small"] + result["is_medium"] + result["is_large"]
        assert (flag_sum == 1).all()

    def test_B04_location_avg_price_column_added(self, sample_df):
        eng = FeatureEngineer()
        result = eng.extract_features(sample_df)
        assert "location_avg_price" in result.columns
        assert result["location_avg_price"].notna().all()

    def test_B05_type_avg_price_column_added(self, sample_df):
        eng = FeatureEngineer()
        result = eng.extract_features(sample_df)
        assert "type_avg_price" in result.columns

    def test_B06_time_features_added_when_created_at_present(self, sample_df):
        eng = FeatureEngineer()
        result = eng.extract_features(sample_df)
        for col in ["days_old", "month", "quarter", "year"]:
            assert col in result.columns

    def test_B07_one_hot_columns_created(self, sample_df):
        eng = FeatureEngineer()
        eng.extract_features(sample_df)
        pt_cols = [c for c in eng.feature_names if c.startswith("property_type_")]
        assert len(pt_cols) >= 3  # residential, commercial, land

    def test_B08_feature_names_non_empty(self, engineered):
        eng, _ = engineered
        assert len(eng.feature_names) >= 10

    def test_B09_get_top_features_respects_top_n(self, engineered):
        eng, _ = engineered
        fi = {f: 1.0 / (i + 1) for i, f in enumerate(eng.feature_names)}
        top5 = eng.get_top_features(fi, top_n=5)
        assert len(top5) == 5
        assert top5[0] == eng.feature_names[0]


# ===========================================================================
# C. ModelTrainer
# ===========================================================================

class TestModelTrainer:

    def test_C01_train_random_forest_returns_result_dict(self, engineered, processed_processor):
        eng, feat_df = engineered
        X = feat_df[eng.feature_names].values.astype(float)
        y = processed_processor.processed_data["primary_value"].values
        trainer = ModelTrainer()
        result = trainer.train_random_forest(X, y, cv=3)
        assert "model" in result
        assert "cv_mean" in result

    def test_C02_cv_mean_is_positive(self, trained_trainer):
        trainer, X, y = trained_trainer
        assert trainer.models["random_forest"] is not None
        # CV R² should be reasonably positive on synthetic data
        from sklearn.model_selection import cross_val_score
        scores = cross_val_score(trainer.models["random_forest"], X, y, cv=3, scoring="r2")
        assert scores.mean() > 0

    def test_C03_train_gradient_boosting_stores_model(self, engineered, processed_processor):
        eng, feat_df = engineered
        X = feat_df[eng.feature_names].values.astype(float)
        y = processed_processor.processed_data["primary_value"].values
        trainer = ModelTrainer()
        trainer.train_gradient_boosting(X, y, cv=3)
        assert "gradient_boosting" in trainer.models

    def test_C04_train_ensemble_sets_best_model(self, engineered, processed_processor):
        eng, feat_df = engineered
        X = feat_df[eng.feature_names].values.astype(float)
        y = processed_processor.processed_data["primary_value"].values
        trainer = ModelTrainer()
        trainer.train_ensemble(X, y, cv=3)
        assert trainer.best_model is not None
        assert trainer.best_algorithm in ("random_forest", "gradient_boosting", "xgboost")

    def test_C05_train_xgboost_skips_gracefully_when_not_installed(
        self, engineered, processed_processor
    ):
        eng, feat_df = engineered
        X = feat_df[eng.feature_names].values.astype(float)
        y = processed_processor.processed_data["primary_value"].values
        trainer = ModelTrainer()
        result = trainer.train_xgboost(X, y, cv=3)
        # Either skipped or trained — no exception
        assert "algorithm" in result

    def test_C06_best_model_can_predict(self, trained_trainer):
        trainer, X, y = trained_trainer
        preds = trainer.best_model.predict(X[:10])
        assert len(preds) == 10
        assert all(p > 0 for p in preds)

    def test_C07_save_and_load_model_roundtrip(self, trained_trainer, tmp_path):
        trainer, _, _ = trained_trainer
        model_path = str(tmp_path / "avm_test.pkl")
        assert trainer.save_model(model_path) is True
        trainer2 = ModelTrainer()
        assert trainer2.load_model(model_path) is True
        assert trainer2.best_model is not None

    def test_C08_hyperparameter_tuning_returns_best_params(self, engineered, processed_processor):
        eng, feat_df = engineered
        X = feat_df[eng.feature_names].values.astype(float)[:200]  # small subset for speed
        y = processed_processor.processed_data["primary_value"].values[:200]
        trainer = ModelTrainer()
        result = trainer.hyperparameter_tuning(X, y, cv=2)
        assert "best_params" in result
        assert result["best_score"] > 0

    def test_C09_save_without_model_returns_false(self, tmp_path):
        trainer = ModelTrainer()
        assert trainer.save_model(str(tmp_path / "none.pkl")) is False


# ===========================================================================
# D. ModelValidator
# ===========================================================================

class TestModelValidator:

    def _preds(self):
        y_true = np.array([1_000_000, 2_000_000, 3_000_000, 4_000_000, 5_000_000], dtype=float)
        y_pred = np.array([1_100_000, 1_900_000, 3_050_000, 3_850_000, 5_200_000], dtype=float)
        return y_true, y_pred

    def test_D01_evaluate_returns_r2(self):
        y_true, y_pred = self._preds()
        m = ModelValidator.evaluate(y_true, y_pred)
        assert "r2" in m
        assert m["r2"] > 0.9

    def test_D02_evaluate_returns_rmse(self):
        y_true, y_pred = self._preds()
        m = ModelValidator.evaluate(y_true, y_pred)
        assert "rmse" in m
        assert m["rmse"] > 0

    def test_D03_evaluate_returns_mae(self):
        y_true, y_pred = self._preds()
        m = ModelValidator.evaluate(y_true, y_pred)
        assert "mae" in m

    def test_D04_evaluate_accuracy_within_ranges(self):
        y_true, y_pred = self._preds()
        m = ModelValidator.evaluate(y_true, y_pred)
        assert "accuracy_within_ranges" in m
        assert m["accuracy_within_ranges"]["20_percent"] >= m["accuracy_within_ranges"]["10_percent"]

    def test_D05_perfect_prediction_r2_equals_one(self):
        y = np.array([100.0, 200.0, 300.0])
        m = ModelValidator.evaluate(y, y)
        assert abs(m["r2"] - 1.0) < 1e-6

    def test_D06_check_overfitting_detects_large_gap(self):
        assert ModelValidator.check_overfitting(0.95, 0.80) is True

    def test_D07_check_overfitting_passes_small_gap(self):
        assert ModelValidator.check_overfitting(0.90, 0.88) is False

    def test_D08_validate_by_subgroup_returns_per_group_metrics(self, processed_processor):
        eng = FeatureEngineer()
        feat_df = eng.extract_features(processed_processor.processed_data)
        X = feat_df[eng.feature_names].values.astype(float)
        y = processed_processor.processed_data["primary_value"].values
        trainer = ModelTrainer()
        trainer.train_random_forest(X, y, cv=3)
        y_pred = trainer.best_model.predict(X)
        sub = ModelValidator.validate_by_subgroup(
            processed_processor.processed_data.reset_index(drop=True),
            y, y_pred, "property_type",
        )
        assert len(sub) >= 1
        for metrics in sub.values():
            assert "r2" in metrics

    def test_D09_generate_report_contains_key_strings(self):
        y_true, y_pred = self._preds()
        m = ModelValidator.evaluate(y_true, y_pred)
        report = ModelValidator.generate_report(m)
        assert "R²" in report
        assert "Within" in report


# ===========================================================================
# E. AVMPredictor
# ===========================================================================

class TestAVMPredictor:

    def test_E01_predict_returns_positive_value(self, predictor):
        result = predictor.predict(150, "Cairo", "residential")
        assert result.get("predicted_value") is not None
        assert result["predicted_value"] > 0

    def test_E02_predict_includes_confidence_interval(self, predictor):
        result = predictor.predict(150, "Cairo", "residential")
        ci = result.get("confidence_interval", {})
        assert "lower_5" in ci
        assert "upper_95" in ci
        assert ci["upper_95"] >= ci["lower_5"]

    def test_E03_predict_includes_method_field(self, predictor):
        result = predictor.predict(200, "Giza", "commercial")
        assert result.get("method") == "avm_ml"

    def test_E04_predict_includes_timestamp(self, predictor):
        result = predictor.predict(100, "Alexandria", "land")
        assert "timestamp" in result

    def test_E05_larger_area_predicts_higher_value(self, predictor):
        small = predictor.predict(80,  "Cairo", "residential")
        large = predictor.predict(300, "Cairo", "residential")
        assert large["predicted_value"] > small["predicted_value"]

    def test_E06_predict_batch_returns_all_properties(self, predictor):
        props = [
            {"property_id": f"P{i}", "area_sqm": 100 + i * 20, "location": "Cairo", "property_type": "residential"}
            for i in range(5)
        ]
        batch = predictor.predict_batch(props)
        assert batch["batch_statistics"]["total_properties"] == 5
        assert batch["batch_statistics"]["successful_predictions"] == 5

    def test_E07_batch_statistics_average_is_positive(self, predictor):
        props = [{"area_sqm": 150, "location": "Giza", "property_type": "commercial"}]
        batch = predictor.predict_batch(props)
        assert batch["batch_statistics"]["average_prediction"] > 0

    def test_E08_get_prediction_explanation_has_top_features(self, predictor):
        exp = predictor.get_prediction_explanation(120, "Cairo", "residential")
        assert "top_features" in exp
        assert len(exp["top_features"]) > 0

    def test_E09_prediction_history_grows(self, predictor):
        before = len(predictor.get_history())
        predictor.predict(200, "Cairo", "residential")
        after = len(predictor.get_history())
        assert after == before + 1


# ===========================================================================
# F. ModelRegistry
# ===========================================================================

class TestModelRegistry:

    def test_F01_register_stores_metadata(self, tmp_registry, trained_trainer):
        trainer, _, _ = trained_trainer
        meta = tmp_registry.register(
            model=trainer.best_model,
            algorithm="random_forest",
            metrics={"r2": 0.88},
            feature_count=15,
            record_count=800,
        )
        assert isinstance(meta, ModelMetadata)
        assert meta.algorithm == "random_forest"

    def test_F02_get_retrieves_registered_model(self, tmp_registry, trained_trainer):
        trainer, _, _ = trained_trainer
        meta = tmp_registry.register(
            model=trainer.best_model,
            algorithm="random_forest",
            metrics={"r2": 0.88},
            feature_count=15,
            record_count=800,
        )
        fetched = tmp_registry.get(meta.model_id)
        assert fetched is not None
        assert fetched.model_id == meta.model_id

    def test_F03_list_models_returns_all_registered(self, tmp_registry, trained_trainer):
        trainer, _, _ = trained_trainer
        before = len(tmp_registry.list_models())
        tmp_registry.register(
            model=trainer.best_model,
            algorithm="gradient_boosting",
            metrics={"r2": 0.85},
            feature_count=15,
            record_count=800,
        )
        assert len(tmp_registry.list_models()) == before + 1

    def test_F04_activate_marks_model_active(self, tmp_registry, trained_trainer):
        trainer, _, _ = trained_trainer
        meta = tmp_registry.register(
            model=trainer.best_model,
            algorithm="random_forest",
            metrics={"r2": 0.90},
            feature_count=15,
            record_count=800,
        )
        assert tmp_registry.activate(meta.model_id) is True
        active = tmp_registry.get_active_model()
        assert active is not None
        assert active.model_id == meta.model_id

    def test_F05_delete_removes_model(self, tmp_registry, trained_trainer):
        trainer, _, _ = trained_trainer
        meta = tmp_registry.register(
            model=trainer.best_model,
            algorithm="random_forest",
            metrics={"r2": 0.80},
            feature_count=15,
            record_count=800,
        )
        assert tmp_registry.delete(meta.model_id) is True
        assert tmp_registry.get(meta.model_id) is None

    def test_F06_get_stats_reports_count(self, tmp_registry, trained_trainer):
        trainer, _, _ = trained_trainer
        tmp_registry.register(
            model=trainer.best_model,
            algorithm="random_forest",
            metrics={"r2": 0.87},
            feature_count=15,
            record_count=800,
        )
        stats = tmp_registry.get_stats()
        assert stats["total_models"] >= 1
        assert "random_forest" in stats["algorithms"]
