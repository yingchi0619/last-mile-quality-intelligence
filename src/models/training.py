"""Train baseline and nonlinear prototype route-risk models."""

from __future__ import annotations

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .config import CATEGORICAL_FEATURES, NUMERIC_FEATURES, LateDeliveryModelConfig


def _feature_transformer(scale_numeric: bool) -> ColumnTransformer:
    numeric_transformer = StandardScaler() if scale_numeric else "passthrough"
    return ColumnTransformer(
        [
            ("numeric", numeric_transformer, NUMERIC_FEATURES),
            ("categorical", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )


def build_models(config: LateDeliveryModelConfig) -> dict[str, Pipeline]:
    """Return an interpretable baseline and a nonlinear comparison model."""
    logistic = Pipeline(
        [
            ("features", _feature_transformer(scale_numeric=True)),
            (
                "classifier",
                LogisticRegression(
                    max_iter=2_000,
                    class_weight="balanced",
                    random_state=config.random_seed,
                ),
            ),
        ]
    )
    random_forest = Pipeline(
        [
            ("features", _feature_transformer(scale_numeric=False)),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=300,
                    max_depth=9,
                    min_samples_leaf=8,
                    class_weight="balanced_subsample",
                    random_state=config.random_seed,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    return {"logistic_regression": logistic, "random_forest": random_forest}
