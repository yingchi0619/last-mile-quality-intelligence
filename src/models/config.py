"""Configuration for the prototype late-delivery risk model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LateDeliveryModelConfig:
    target_otd_threshold: float = 0.85
    train_date_fraction: float = 0.75
    random_seed: int = 20250317
    classification_threshold: float = 0.50


NUMERIC_FEATURES = [
    "planned_packages",
    "expected_capacity_utilization",
    "route_distance_miles",
    "route_density",
    "pickup_delay_minutes",
    "driver_historical_reliability",
    "dsp_historical_otd",
    "station_historical_otd",
]

CATEGORICAL_FEATURES = ["provider_id", "station_id", "day_of_week"]
MODEL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
