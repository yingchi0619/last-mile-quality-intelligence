"""Segmented KPI analysis across numeric and categorical operating factors."""

from __future__ import annotations

import pandas as pd

from ..kpis import NUMERIC_FACTORS


def _aggregate(grouped: pd.core.groupby.DataFrameGroupBy) -> pd.DataFrame:
    result = grouped.agg(
        route_count=("route_id", "size"),
        packages=("package_records", "sum"),
        active_drivers=("driver_id", "nunique"),
        on_time_packages=("on_time_packages", "sum"),
        delivered_packages=("delivered_packages", "sum"),
        exception_packages=("exception_packages", "sum"),
        average_pickup_delay=("pickup_delay_minutes", "mean"),
        average_utilization=("capacity_utilization", "mean"),
        average_route_density=("route_density", "mean"),
    ).reset_index()
    result["on_time_delivery_rate"] = result["on_time_packages"] / result["packages"]
    result["delivery_success_rate"] = result["delivered_packages"] / result["packages"]
    result["exception_rate"] = result["exception_packages"] / result["packages"]
    # Each route has one assigned driver; use driver-route assignments so
    # density segment productivity remains comparable over the full 90 days.
    result["packages_per_driver"] = result["packages"] / result["route_count"]
    return result


def segmented_kpi_analysis(routes: pd.DataFrame) -> pd.DataFrame:
    """Create comparable low/mid/high and categorical KPI segments."""
    frames: list[pd.DataFrame] = []
    for factor in NUMERIC_FACTORS:
        labels = ["LOW", "MEDIUM", "HIGH"]
        segment = pd.qcut(routes[factor], q=3, labels=labels, duplicates="drop")
        working = routes.assign(segment=segment.astype(str))
        summary = _aggregate(working.groupby("segment", observed=True))
        summary.insert(0, "factor", factor)
        frames.append(summary)

    for factor, source in [
        ("DSP", "provider_id"),
        ("station", "station_id"),
        ("day_of_week", "day_of_week"),
    ]:
        working = routes.assign(segment=routes[source].astype(str))
        summary = _aggregate(working.groupby("segment", observed=True))
        summary.insert(0, "factor", factor)
        frames.append(summary)
    return pd.concat(frames, ignore_index=True)
