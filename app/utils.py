"""Dashboard metric transformations."""

from __future__ import annotations

import numpy as np
import pandas as pd


def aggregate_kpis(data: pd.DataFrame) -> dict[str, float]:
    packages = data["package_records"].sum()
    delivered = data["delivered_packages"].sum()
    daily_driver_load = data.groupby("service_date").apply(
        lambda frame: frame["actual_packages"].sum() / frame["driver_id"].nunique(),
        include_groups=False,
    ) if len(data) else pd.Series(dtype=float)
    return {
        "otd": data["on_time_packages"].sum() / packages if packages else np.nan,
        "success": delivered / packages if packages else np.nan,
        "pod": data["pod_compliant_packages"].sum() / delivered if delivered else np.nan,
        "exception": data["exception_packages"].sum() / packages if packages else np.nan,
        "utilization": data["actual_packages"].sum() / data["planned_capacity"].sum() if len(data) else np.nan,
        "packages_per_driver": daily_driver_load.mean() if len(daily_driver_load) else np.nan,
        "pickup_delay": data["pickup_delay_minutes"].mean() if len(data) else np.nan,
    }


def prior_period(all_data: pd.DataFrame, current: pd.DataFrame) -> pd.DataFrame:
    if current.empty:
        return current
    start, end = current["service_date"].min(), current["service_date"].max()
    days = (end - start).days + 1
    prior_start, prior_end = start - pd.Timedelta(days=days), start - pd.Timedelta(days=1)
    stations, dsps = current["station_id"].unique(), current["provider_id"].unique()
    return all_data[
        all_data["service_date"].between(prior_start, prior_end)
        & all_data["station_id"].isin(stations)
        & all_data["provider_id"].isin(dsps)
    ]


def grouped_performance(data: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    result = data.groupby(group_columns, observed=True).agg(
        routes=("route_line_id", "nunique"), route_assignments=("route_id", "size"), volume=("actual_packages", "sum"),
        capacity=("planned_capacity", "sum"), packages=("package_records", "sum"),
        on_time=("on_time_packages", "sum"), delivered=("delivered_packages", "sum"),
        pod=("pod_compliant_packages", "sum"), exceptions=("exception_packages", "sum"),
        active_drivers=("driver_id", "nunique"), pickup_delay=("pickup_delay_minutes", "mean"),
        route_density=("route_density", "mean"),
    ).reset_index()
    result["otd"] = result["on_time"] / result["packages"]
    result["success"] = result["delivered"] / result["packages"]
    result["pod_compliance"] = result["pod"] / result["delivered"]
    result["exception_rate"] = result["exceptions"] / result["packages"]
    result["utilization"] = result["volume"] / result["capacity"]
    result["packages_per_driver"] = result["volume"] / result["active_drivers"]
    return result


def daily_performance(data: pd.DataFrame) -> pd.DataFrame:
    daily = grouped_performance(data, ["service_date"])
    daily["rolling_7d_otd"] = daily["otd"].rolling(7, min_periods=1).mean()
    daily["rolling_30d_otd"] = daily["otd"].rolling(30, min_periods=1).mean()
    daily["rolling_7d_exception"] = daily["exception_rate"].rolling(7, min_periods=1).mean()
    return daily
