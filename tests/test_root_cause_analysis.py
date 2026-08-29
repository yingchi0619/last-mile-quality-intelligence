"""Tests for data-derived operational RCA outputs and narrative consistency."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.analytics.rca import run_root_cause_analysis
from src.analytics.rca.data_access import load_route_factors
from src.analytics.rca.segmentation import segmented_kpi_analysis
from src.analytics.rca.thresholds import threshold_analysis


def test_threshold_impacts_reconcile_to_route_facts() -> None:
    routes = load_route_factors()
    thresholds = threshold_analysis(routes)
    capacity = thresholds.loc[thresholds["factor"] == "capacity_utilization"].iloc[0]
    exposed = routes[routes["capacity_utilization"] > capacity["threshold"]]
    baseline = routes[routes["capacity_utilization"] <= capacity["threshold"]]
    expected_exposed_otd = exposed["on_time_packages"].sum() / exposed["package_records"].sum()
    expected_baseline_otd = baseline["on_time_packages"].sum() / baseline["package_records"].sum()
    assert capacity["exposed_otd"] == pytest.approx(expected_exposed_otd)
    assert capacity["baseline_otd"] == pytest.approx(expected_baseline_otd)
    assert capacity["otd_impact_percentage_points"] == pytest.approx(
        (expected_baseline_otd - expected_exposed_otd) * 100
    )


def test_density_productivity_is_route_normalized() -> None:
    routes = load_route_factors()
    segments = segmented_kpi_analysis(routes)
    density = segments[segments["factor"] == "route_density"].set_index("segment")
    for segment in ["LOW", "MEDIUM", "HIGH"]:
        expected = density.loc[segment, "packages"] / density.loc[segment, "route_count"]
        assert density.loc[segment, "packages_per_driver"] == pytest.approx(expected)


def test_pipeline_writes_complete_manager_outputs(tmp_path: Path) -> None:
    manifest = run_root_cause_analysis(output_dir=tmp_path)
    expected_files = {
        "correlation_analysis.csv",
        "segmented_kpi_analysis.csv",
        "threshold_analysis.csv",
        "week_over_week_trends.csv",
        "rolling_average_analysis.csv",
        "zscore_anomalies.csv",
        "exception_pareto_analysis.csv",
        "dsp_benchmark.csv",
        "station_benchmark.csv",
        "operational_insights_summary.md",
        "rca_manifest.json",
    }
    assert expected_files == {path.name for path in tmp_path.iterdir()}
    assert manifest["route_count"] == len(load_route_factors())
    thresholds = pd.read_csv(tmp_path / "threshold_analysis.csv")
    capacity = thresholds.loc[thresholds["factor"] == "capacity_utilization"].iloc[0]
    summary = (tmp_path / "operational_insights_summary.md").read_text(encoding="utf-8")
    assert f"{capacity['threshold'] * 100:.1f}%" in summary
    assert f"{capacity['otd_impact_percentage_points']:.1f} percentage points" in summary
