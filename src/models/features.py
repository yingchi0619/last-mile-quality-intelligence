"""Leakage-safe feature engineering for route risk prediction."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import pandas as pd

from src.analytics.sql_runner import execute_query

from .config import LateDeliveryModelConfig

PathLike = Union[str, Path]


def _prior_entity_otd(
    routes: pd.DataFrame,
    entity_column: str,
    output_column: str,
    fallback: pd.Series,
) -> pd.DataFrame:
    daily = (
        routes.groupby([entity_column, "service_date"], as_index=False)
        .agg(on_time_packages=("on_time_packages", "sum"), package_records=("package_records", "sum"))
        .sort_values([entity_column, "service_date"])
    )
    daily["prior_on_time"] = daily.groupby(entity_column)["on_time_packages"].transform(
        lambda values: values.cumsum().shift(1)
    )
    daily["prior_packages"] = daily.groupby(entity_column)["package_records"].transform(
        lambda values: values.cumsum().shift(1)
    )
    daily[output_column] = daily["prior_on_time"] / daily["prior_packages"]
    daily[output_column] = daily[output_column].fillna(daily["service_date"].map(fallback))
    return daily[[entity_column, "service_date", output_column]]


def build_model_dataset(
    database_path: Optional[PathLike] = None,
    config: Optional[LateDeliveryModelConfig] = None,
) -> pd.DataFrame:
    """Build features known by dispatch/route start and a post-route target."""
    config = config or LateDeliveryModelConfig()
    routes = execute_query(
        """
        SELECT
            route_id,
            service_date,
            provider_id,
            station_id,
            planned_packages,
            planned_capacity,
            planned_packages::DOUBLE / NULLIF(planned_capacity, 0) AS expected_capacity_utilization,
            route_distance_miles,
            route_density,
            pickup_delay_minutes,
            driver_reliability AS driver_historical_reliability,
            package_records,
            on_time_packages,
            delivered_packages,
            on_time_delivery_rate
        FROM route_performance
        ORDER BY service_date, route_id
        """,
        database_path,
    )
    routes["service_date"] = pd.to_datetime(routes["service_date"])
    routes["day_of_week"] = routes["service_date"].dt.day_name()

    regional_daily = (
        routes.groupby("service_date", as_index=False)
        .agg(on_time_packages=("on_time_packages", "sum"), package_records=("package_records", "sum"))
        .sort_values("service_date")
    )
    regional_daily["prior_on_time"] = regional_daily["on_time_packages"].cumsum().shift(1)
    regional_daily["prior_packages"] = regional_daily["package_records"].cumsum().shift(1)
    regional_daily["prior_regional_otd"] = regional_daily["prior_on_time"] / regional_daily["prior_packages"]
    regional_fallback = regional_daily.set_index("service_date")["prior_regional_otd"].fillna(config.target_otd_threshold)

    dsp_history = _prior_entity_otd(routes, "provider_id", "dsp_historical_otd", regional_fallback)
    station_history = _prior_entity_otd(routes, "station_id", "station_historical_otd", regional_fallback)
    dataset = routes.merge(dsp_history, on=["provider_id", "service_date"], how="left")
    dataset = dataset.merge(station_history, on=["station_id", "service_date"], how="left")
    dataset["late_route_flag"] = (dataset["on_time_delivery_rate"] < config.target_otd_threshold).astype("int8")
    return dataset


def chronological_train_test_split(
    dataset: pd.DataFrame,
    train_fraction: float = 0.75,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    """Split by complete service dates so the test period is strictly later."""
    if not 0.5 <= train_fraction < 1.0:
        raise ValueError("train_fraction must be between 0.5 and 1.0.")
    dates = pd.Index(sorted(dataset["service_date"].unique()))
    train_date_count = int(len(dates) * train_fraction)
    cutoff = pd.Timestamp(dates[train_date_count - 1])
    train = dataset[dataset["service_date"] <= cutoff].copy()
    test = dataset[dataset["service_date"] > cutoff].copy()
    if train.empty or test.empty:
        raise ValueError("Chronological split produced an empty train or test set.")
    return train, test, cutoff
