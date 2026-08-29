"""Tests for reproducibility and relational quality of synthetic data."""

import pandas as pd
from src.data_generation import GenerationConfig, generate_all


def test_generation_meets_scale_and_quality_requirements() -> None:
    tables, report = generate_all()
    assert len(tables["stations"]) == 3
    assert len(tables["delivery_service_providers"]) == 4
    assert 80 <= len(tables["drivers"]) <= 120
    assert len(tables["deliveries"]) >= 200_000
    assert tables["routes"]["service_date"].nunique() == 90
    assert report.passed


def test_generation_is_reproducible() -> None:
    config = GenerationConfig(days=3)
    first, _ = generate_all(config)
    second, _ = generate_all(config)
    for table_name in first:
        pd.testing.assert_frame_equal(first[table_name], second[table_name])


def test_designed_operational_relationships_are_visible() -> None:
    tables, _ = generate_all()
    routes, deliveries = tables["routes"], tables["deliveries"]
    route_otd = deliveries.groupby("route_id")["on_time_flag"].mean().rename("otd")
    performance = routes.join(route_otd, on="route_id")
    performance["utilization"] = performance["actual_packages"] / performance["planned_capacity"]
    assert performance.loc[performance["route_density"] > 1.5, "otd"].mean() > performance.loc[performance["route_density"] < 1.0, "otd"].mean()
    assert performance.loc[performance["pickup_delay_minutes"] < 5, "otd"].mean() > performance.loc[performance["pickup_delay_minutes"] > 25, "otd"].mean()
    assert performance.loc[performance["utilization"] <= 0.95, "otd"].mean() > performance.loc[performance["utilization"] > 1.05, "otd"].mean()
