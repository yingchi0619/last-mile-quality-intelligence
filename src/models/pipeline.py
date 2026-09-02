"""End-to-end training, evaluation, scoring, and artifact output."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from src.analytics.database import DEFAULT_DATABASE, project_root

from .config import MODEL_FEATURES, LateDeliveryModelConfig
from .evaluation import evaluate_classifier, feature_importance
from .features import build_model_dataset, chronological_train_test_split
from .training import build_models

PathLike = Union[str, Path]


def run_late_delivery_model(
    database_path: Optional[PathLike] = None,
    output_dir: Optional[PathLike] = None,
    config: Optional[LateDeliveryModelConfig] = None,
) -> dict[str, object]:
    """Train both prototypes and score the strictly later holdout period."""
    config = config or LateDeliveryModelConfig()
    root = project_root()
    database = Path(database_path) if database_path else root / DEFAULT_DATABASE
    if not database.is_absolute():
        database = root / database
    target = Path(output_dir) if output_dir else root / "data" / "processed" / "late_delivery_model"
    if not target.is_absolute():
        target = root / target
    target.mkdir(parents=True, exist_ok=True)

    dataset = build_model_dataset(database, config)
    train, test, cutoff = chronological_train_test_split(dataset, config.train_date_fraction)
    model_train, validation, selection_cutoff = chronological_train_test_split(train, 0.80)
    x_train, y_train = train[MODEL_FEATURES], train["late_route_flag"]
    x_test, y_test = test[MODEL_FEATURES], test["late_route_flag"]
    models = build_models(config)
    validation_auc: dict[str, float] = {}
    for model_name, model in models.items():
        model.fit(model_train[MODEL_FEATURES], model_train["late_route_flag"])
        validation_auc[model_name] = roc_auc_score(
            validation["late_route_flag"],
            model.predict_proba(validation[MODEL_FEATURES])[:, 1],
        )
    selected_model = max(validation_auc, key=validation_auc.get)

    metric_rows: list[dict[str, object]] = []
    confusion_frames: list[pd.DataFrame] = []
    importance_frames: list[pd.DataFrame] = []
    test_scores: dict[str, np.ndarray] = {}
    train_scores: dict[str, np.ndarray] = {}

    for model_name, model in models.items():
        model.fit(x_train, y_train)
        test_probability = model.predict_proba(x_test)[:, 1]
        train_probability = model.predict_proba(x_train)[:, 1]
        metrics, confusion = evaluate_classifier(
            model_name, y_test, test_probability, config.classification_threshold
        )
        metrics["validation_roc_auc"] = validation_auc[model_name]
        metric_rows.append(metrics)
        confusion_frames.append(confusion)
        importance_frames.append(feature_importance(model_name, model))
        test_scores[model_name] = test_probability
        train_scores[model_name] = train_probability
        joblib.dump(model, target / f"{model_name}.joblib")

    metrics_frame = pd.DataFrame(metric_rows).sort_values("roc_auc", ascending=False).reset_index(drop=True)
    low_medium_cutoff, medium_high_cutoff = np.quantile(
        train_scores[selected_model], [0.50, 0.80]
    )
    predictions = test[
        ["route_id", "route_line_id", "service_date", "station_id", "provider_id", "late_route_flag", "on_time_delivery_rate"]
    ].copy()
    for model_name, scores in test_scores.items():
        predictions[f"{model_name}_risk_score"] = scores
    predictions["selected_model"] = selected_model
    predictions["late_delivery_risk_score"] = test_scores[selected_model]
    predictions["risk_tier"] = pd.cut(
        predictions["late_delivery_risk_score"],
        bins=[-np.inf, low_medium_cutoff, medium_high_cutoff, np.inf],
        labels=["Low Risk", "Medium Risk", "High Risk"],
        include_lowest=True,
    ).astype(str)

    metrics_frame.to_csv(target / "model_metrics.csv", index=False)
    pd.concat(confusion_frames, ignore_index=True).to_csv(target / "confusion_matrices.csv", index=False)
    pd.concat(importance_frames, ignore_index=True).to_csv(target / "feature_importance.csv", index=False)
    predictions.to_csv(target / "route_risk_scores.csv", index=False)
    predictions.to_parquet(target / "route_risk_scores.parquet", index=False)
    joblib.dump(models[selected_model], target / "selected_late_delivery_model.joblib")

    metadata = {
        "prototype_disclaimer": "This is a portfolio prototype, not a production-ready AI or operational decision system.",
        "target_definition": f"late_route_flag = 1 when route-level OTD is below {config.target_otd_threshold:.0%}",
        "feature_timing": "Features are limited to signals known before dispatch or at route start; pickup delay is treated as a route-start signal.",
        "leakage_controls": [
            "Chronological model-selection, validation, and holdout split by complete service date",
            "Expected utilization uses planned packages divided by planned capacity",
            "DSP and station historical OTD use prior dates only",
            "No actual packages, delivery status, final timestamps, or post-route KPI is used as a feature",
        ],
        "config": asdict(config),
        "train_rows": len(train),
        "test_rows": len(test),
        "train_start": str(train["service_date"].min().date()),
        "train_end": str(cutoff.date()),
        "model_selection_train_end": str(selection_cutoff.date()),
        "validation_start": str(validation["service_date"].min().date()),
        "validation_end": str(validation["service_date"].max().date()),
        "selection_rule": "Highest ROC-AUC on the internal chronological validation window",
        "test_start": str(test["service_date"].min().date()),
        "test_end": str(test["service_date"].max().date()),
        "selected_model": selected_model,
        "risk_tier_cutoffs": {
            "low_medium": float(low_medium_cutoff),
            "medium_high": float(medium_high_cutoff),
            "source": "Selected model training-score quantiles (50th and 80th percentiles)",
        },
        "test_late_route_rate": float(y_test.mean()),
    }
    (target / "model_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    _write_model_summary(target, metrics_frame, metadata, predictions)
    return {"metrics": metric_rows, "metadata": metadata, "prediction_rows": len(predictions)}


def _write_model_summary(
    output_dir: Path,
    metrics: pd.DataFrame,
    metadata: dict[str, object],
    predictions: pd.DataFrame,
) -> None:
    lines = [
        "# Late Delivery Risk Model — Prototype Results",
        "",
        "A prototype demonstrating how pre-dispatch operational signals can be used to identify potentially high-risk routes.",
        "",
        f"**Train period:** {metadata['train_start']} to {metadata['train_end']}  ",
        f"**Test period:** {metadata['test_start']} to {metadata['test_end']}  ",
        f"**Selected model:** {metadata['selected_model']}",
        "",
        "## Holdout performance",
        "",
        "| Model | Validation ROC-AUC | Holdout ROC-AUC | Precision | Recall | F1 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in metrics.itertuples(index=False):
        lines.append(
            f"| {row.model} | {row.validation_roc_auc:.3f} | {row.roc_auc:.3f} | {row.precision:.3f} | {row.recall:.3f} | {row.f1_score:.3f} |"
        )
    tier_counts = predictions["risk_tier"].value_counts()
    lines.extend(
        [
            "",
            "## Holdout risk tiers",
            "",
            *[f"- {tier}: {int(tier_counts.get(tier, 0)):,} routes" for tier in ["Low Risk", "Medium Risk", "High Risk"]],
            "",
            "> This is a portfolio prototype, not a production-ready AI or operational decision system.",
        ]
    )
    (output_dir / "model_summary.md").write_text("\n".join(lines), encoding="utf-8")
