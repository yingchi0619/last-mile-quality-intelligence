"""Tests for leakage controls, model evaluation, and route risk outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.models.config import MODEL_FEATURES, LateDeliveryModelConfig
from src.models.features import build_model_dataset, chronological_train_test_split
from src.models.pipeline import run_late_delivery_model


def test_feature_set_excludes_post_route_information() -> None:
    prohibited = {
        "actual_packages",
        "delivery_status",
        "delivery_timestamp",
        "on_time_delivery_rate",
        "late_route_flag",
        "exception_rate",
    }
    assert prohibited.isdisjoint(MODEL_FEATURES)
    dataset = build_model_dataset()
    assert dataset[MODEL_FEATURES].isna().sum().sum() == 0
    assert dataset["expected_capacity_utilization"].iloc[0] == pytest.approx(
        dataset["planned_packages"].iloc[0] / dataset["planned_capacity"].iloc[0]
    )


def test_historical_dsp_feature_uses_prior_dates_only() -> None:
    dataset = build_model_dataset()
    dates = sorted(dataset["service_date"].unique())
    first_date, second_date = dates[0], dates[1]
    provider = dataset.loc[dataset["service_date"] == second_date, "provider_id"].iloc[0]
    prior = dataset[
        (dataset["service_date"] == first_date) & (dataset["provider_id"] == provider)
    ]
    expected_prior_otd = prior["on_time_packages"].sum() / prior["package_records"].sum()
    actual_feature = dataset.loc[
        (dataset["service_date"] == second_date) & (dataset["provider_id"] == provider),
        "dsp_historical_otd",
    ].iloc[0]
    assert actual_feature == pytest.approx(expected_prior_otd)


def test_chronological_split_has_no_date_overlap() -> None:
    dataset = build_model_dataset()
    train, test, cutoff = chronological_train_test_split(dataset)
    assert train["service_date"].max() == cutoff
    assert train["service_date"].max() < test["service_date"].min()
    assert set(train["service_date"]).isdisjoint(set(test["service_date"]))


def test_model_pipeline_outputs_scores_and_comparative_metrics(tmp_path: Path) -> None:
    result = run_late_delivery_model(output_dir=tmp_path)
    expected_files = {
        "logistic_regression.joblib",
        "random_forest.joblib",
        "selected_late_delivery_model.joblib",
        "model_metrics.csv",
        "confusion_matrices.csv",
        "feature_importance.csv",
        "route_risk_scores.csv",
        "route_risk_scores.parquet",
        "model_metadata.json",
        "model_summary.md",
    }
    assert expected_files == {path.name for path in tmp_path.iterdir()}
    metrics = pd.read_csv(tmp_path / "model_metrics.csv")
    assert set(metrics["model"]) == {"logistic_regression", "random_forest"}
    assert metrics[["roc_auc", "precision", "recall", "f1_score"]].apply(
        lambda column: column.between(0, 1).all()
    ).all()
    predictions = pd.read_csv(tmp_path / "route_risk_scores.csv")
    assert predictions["late_delivery_risk_score"].between(0, 1).all()
    assert set(predictions["risk_tier"]) <= {"Low Risk", "Medium Risk", "High Risk"}
    assert result["prediction_rows"] == len(predictions)
