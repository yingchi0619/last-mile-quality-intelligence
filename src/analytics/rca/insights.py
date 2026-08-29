"""Translate computed RCA results into manager-facing operational language."""

from __future__ import annotations

import pandas as pd


def _pp(value: float) -> str:
    return f"{abs(value):.1f} percentage points"


def _threshold_sentence(row: pd.Series) -> str:
    factor = row["factor"]
    threshold = row["threshold"]
    direction = "above" if row["risk_direction"] == "HIGH" else "below"
    if factor in {"capacity_utilization", "driver_reliability"}:
        displayed = f"{threshold * 100:.1f}%"
    elif factor == "pickup_delay_minutes":
        displayed = f"{threshold:.1f} minutes"
    else:
        displayed = f"{threshold:.1f}"
    factor_label = "pickup delay" if factor == "pickup_delay_minutes" else factor.replace("_", " ")
    return (
        f"When {factor_label} is {direction} {displayed}, OTD is "
        f"{_pp(row['otd_impact_percentage_points'])} lower than the comparison group "
        f"({row['exposed_otd']:.1%} vs. {row['baseline_otd']:.1%})."
    )


def build_operational_insights_summary(
    routes: pd.DataFrame,
    thresholds: pd.DataFrame,
    segments: pd.DataFrame,
    trends: pd.DataFrame,
    anomalies: pd.DataFrame,
    pareto: pd.DataFrame,
    dsp_benchmark: pd.DataFrame,
    station_benchmark: pd.DataFrame,
) -> str:
    """Build an entirely data-derived summary for a Regional Operations Manager."""
    date_min = pd.Timestamp(routes["service_date"].min()).date()
    date_max = pd.Timestamp(routes["service_date"].max()).date()
    regional_otd = routes["on_time_packages"].sum() / routes["package_records"].sum()
    regional_success = routes["delivered_packages"].sum() / routes["package_records"].sum()
    regional_exception = routes["exception_packages"].sum() / routes["package_records"].sum()

    priority_lines: list[str] = []
    for factor in ["capacity_utilization", "pickup_delay_minutes"]:
        match = thresholds[thresholds["factor"] == factor]
        if not match.empty:
            priority_lines.append(_threshold_sentence(match.iloc[0]))

    density = segments[segments["factor"] == "route_density"].set_index("segment")
    if {"LOW", "HIGH"}.issubset(density.index):
        low_ppd = density.loc["LOW", "packages_per_driver"]
        high_ppd = density.loc["HIGH", "packages_per_driver"]
        priority_lines.append(
            f"Low-density routes handled {low_ppd:.1f} packages per active driver versus "
            f"{high_ppd:.1f} on high-density routes, a {abs(high_ppd - low_ppd):.1f}-package productivity gap."
        )

    dsp_trends = trends[trends["entity_type"] == "DSP"].sort_values("otd_change_percentage_points")
    if not dsp_trends.empty:
        worst = dsp_trends.iloc[0]
        direction = "down" if worst["otd_change_percentage_points"] < 0 else "up"
        priority_lines.append(
            f"{worst['entity_id']} has the weakest recent trend: latest 7-day OTD is "
            f"{worst['recent_7d_otd']:.1%}, {direction} {_pp(worst['otd_change_percentage_points'])} "
            f"versus its preceding 30-day baseline."
        )

    worst_dsp = dsp_benchmark.sort_values("on_time_delivery_rate").iloc[0]
    worst_station = station_benchmark.sort_values("exception_rate", ascending=False).iloc[0]
    top_exception = pareto.iloc[0]
    priority_lines.extend(
        [
            f"{worst_dsp['provider_id']} is the lowest-OTD DSP at {worst_dsp['on_time_delivery_rate']:.1%}, "
            f"{_pp(worst_dsp['otd_vs_region_percentage_points'])} below the regional result.",
            f"{worst_station['station_id']} has the highest station exception rate at {worst_station['exception_rate']:.1%}.",
            f"{top_exception['exception_type']} is the largest exception category, representing {top_exception['exception_share']:.1%} of exceptions.",
        ]
    )

    anomaly_line = (
        f"The rolling z-score monitor identified {len(anomalies)} material OTD-drop or exception-spike events."
        if len(anomalies)
        else "The rolling z-score monitor found no material OTD-drop or exception-spike events."
    )
    actions = [
        "Prioritize dispatch and load-balancing controls around the data-derived utilization and pickup-delay breakpoints.",
        f"Review route design and coaching plans for {worst_dsp['provider_id']}, with emphasis on pickup execution and density mix.",
        f"Run a focused exception review at {worst_station['station_id']} and address the leading {top_exception['exception_type']} driver first.",
        "Use the rolling trend and anomaly files as a weekly operating-review watchlist; investigate signals before changing targets.",
    ]

    return "\n".join(
        [
            "# Regional Operations Root Cause Summary",
            "",
            f"**Analysis period:** {date_min} to {date_max}  ",
            f"**Scope:** {len(routes):,} routes and {int(routes['package_records'].sum()):,} synthetic packages",
            "",
            "## Regional health",
            "",
            f"Regional OTD was **{regional_otd:.1%}**, delivery success was **{regional_success:.1%}**, "
            f"and exception rate was **{regional_exception:.1%}**.",
            "",
            "## What is driving performance",
            "",
            *[f"- {line}" for line in priority_lines],
            "",
            "## Operational watchlist",
            "",
            f"- {anomaly_line}",
            "",
            "## Recommended operating actions",
            "",
            *[f"{index}. {action}" for index, action in enumerate(actions, start=1)],
            "",
            "All findings are calculated from the project's entirely synthetic dataset; no figures are hard-coded.",
        ]
    )
