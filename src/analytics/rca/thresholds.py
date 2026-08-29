"""Discover data-driven operating thresholds and quantify KPI impact."""

from __future__ import annotations

import numpy as np
import pandas as pd


RISK_DIRECTION = {
    "capacity_utilization": "HIGH",
    "pickup_delay_minutes": "HIGH",
    "route_distance_miles": "HIGH",
    "package_volume": "HIGH",
    "route_density": "LOW",
    "driver_reliability": "LOW",
}


def _weighted_rates(frame: pd.DataFrame) -> tuple[float, float, float]:
    packages = frame["package_records"].sum()
    return (
        frame["on_time_packages"].sum() / packages,
        frame["delivered_packages"].sum() / packages,
        frame["exception_packages"].sum() / packages,
    )


def threshold_analysis(routes: pd.DataFrame) -> pd.DataFrame:
    """Evaluate quantile candidates and retain the largest observed OTD deterioration."""
    rows: list[dict[str, object]] = []
    quantiles = np.arange(0.50, 0.91, 0.05)
    minimum_routes = max(50, int(len(routes) * 0.08))
    for factor, direction in RISK_DIRECTION.items():
        candidates = routes[factor].quantile(quantiles).drop_duplicates()
        factor_rows: list[dict[str, object]] = []
        for threshold in candidates:
            if direction == "HIGH":
                exposed = routes[routes[factor] > threshold]
                baseline = routes[routes[factor] <= threshold]
            else:
                exposed = routes[routes[factor] <= threshold]
                baseline = routes[routes[factor] > threshold]
            if len(exposed) < minimum_routes or len(baseline) < minimum_routes:
                continue
            exposed_rates = _weighted_rates(exposed)
            baseline_rates = _weighted_rates(baseline)
            factor_rows.append(
                {
                    "factor": factor,
                    "risk_direction": direction,
                    "threshold": float(threshold),
                    "exposed_routes": len(exposed),
                    "baseline_routes": len(baseline),
                    "exposed_otd": exposed_rates[0],
                    "baseline_otd": baseline_rates[0],
                    "otd_impact_percentage_points": (baseline_rates[0] - exposed_rates[0]) * 100,
                    "exposed_delivery_success": exposed_rates[1],
                    "baseline_delivery_success": baseline_rates[1],
                    "exposed_exception_rate": exposed_rates[2],
                    "baseline_exception_rate": baseline_rates[2],
                    "exception_impact_percentage_points": (exposed_rates[2] - baseline_rates[2]) * 100,
                }
            )
        if factor_rows:
            rows.append(max(factor_rows, key=lambda item: item["otd_impact_percentage_points"]))
    result = pd.DataFrame(rows)
    result["impact_rank"] = result["otd_impact_percentage_points"].rank(method="dense", ascending=False).astype(int)
    return result.sort_values("impact_rank").reset_index(drop=True)
