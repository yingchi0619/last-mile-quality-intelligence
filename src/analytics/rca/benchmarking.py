"""Package-weighted DSP and station benchmarking."""

from __future__ import annotations

import pandas as pd


def _benchmark(routes: pd.DataFrame, entity_id: str, entity_name: str) -> pd.DataFrame:
    result = routes.groupby([entity_id, entity_name]).agg(
        route_count=("route_id", "size"), packages=("package_records", "sum"),
        active_drivers=("driver_id", "nunique"), on_time_packages=("on_time_packages", "sum"),
        delivered_packages=("delivered_packages", "sum"), exception_packages=("exception_packages", "sum"),
        average_pickup_delay=("pickup_delay_minutes", "mean"), capacity_utilization=("capacity_utilization", "mean"),
        average_route_density=("route_density", "mean"), driver_reliability=("driver_reliability", "mean"),
    ).reset_index()
    result["on_time_delivery_rate"] = result["on_time_packages"] / result["packages"]
    result["delivery_success_rate"] = result["delivered_packages"] / result["packages"]
    result["exception_rate"] = result["exception_packages"] / result["packages"]
    result["packages_per_driver"] = result["packages"] / result["active_drivers"]
    regional_otd = result["on_time_packages"].sum() / result["packages"].sum()
    result["otd_vs_region_percentage_points"] = (result["on_time_delivery_rate"] - regional_otd) * 100
    result["otd_rank"] = result["on_time_delivery_rate"].rank(method="dense", ascending=False).astype(int)
    result["exception_rank"] = result["exception_rate"].rank(method="dense", ascending=True).astype(int)
    return result.sort_values("otd_rank").reset_index(drop=True)


def dsp_station_benchmarking(routes: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    return _benchmark(routes, "provider_id", "provider_name"), _benchmark(routes, "station_id", "station_name")
