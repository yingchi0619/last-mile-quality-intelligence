"""Evaluation and interpretability helpers for route-risk classifiers."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline


def evaluate_classifier(
    model_name: str,
    y_true: pd.Series,
    probabilities: np.ndarray,
    threshold: float = 0.5,
) -> tuple[dict[str, object], pd.DataFrame]:
    predicted = (probabilities >= threshold).astype(int)
    matrix = confusion_matrix(y_true, predicted, labels=[0, 1])
    metrics = {
        "model": model_name,
        "roc_auc": roc_auc_score(y_true, probabilities),
        "precision": precision_score(y_true, predicted, zero_division=0),
        "recall": recall_score(y_true, predicted, zero_division=0),
        "f1_score": f1_score(y_true, predicted, zero_division=0),
        "decision_threshold": threshold,
        "true_negative": int(matrix[0, 0]),
        "false_positive": int(matrix[0, 1]),
        "false_negative": int(matrix[1, 0]),
        "true_positive": int(matrix[1, 1]),
    }
    matrix_frame = pd.DataFrame(
        matrix,
        index=["actual_low_risk", "actual_late_route"],
        columns=["predicted_low_risk", "predicted_late_route"],
    ).reset_index().rename(columns={"index": "actual_class"})
    matrix_frame.insert(0, "model", model_name)
    return metrics, matrix_frame


def feature_importance(model_name: str, pipeline: Pipeline) -> pd.DataFrame:
    """Extract encoded logistic coefficients or Random Forest importance."""
    encoded_names = pipeline.named_steps["features"].get_feature_names_out()
    estimator = pipeline.named_steps["classifier"]
    if hasattr(estimator, "coef_"):
        values = estimator.coef_[0]
        importance_type = "logistic_coefficient"
    else:
        values = estimator.feature_importances_
        importance_type = "impurity_importance"
    result = pd.DataFrame(
        {
            "model": model_name,
            "encoded_feature": encoded_names,
            "importance_type": importance_type,
            "importance_value": values,
            "absolute_importance": np.abs(values),
        }
    )
    result["importance_rank"] = result["absolute_importance"].rank(method="dense", ascending=False).astype(int)
    return result.sort_values("importance_rank").reset_index(drop=True)
