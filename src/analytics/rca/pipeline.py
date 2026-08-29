"""Orchestrate the complete operational root-cause analysis workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from ..database import DEFAULT_DATABASE, build_database, project_root
from .anomalies import zscore_anomaly_detection
from .benchmarking import dsp_station_benchmarking
from .correlation import correlation_analysis
from .data_access import load_exception_facts, load_route_factors
from .insights import build_operational_insights_summary
from .pareto import exception_pareto_analysis
from .segmentation import segmented_kpi_analysis
from .thresholds import threshold_analysis
from .trends import rolling_average_analysis, week_over_week_trends

PathLike = Union[str, Path]


def run_root_cause_analysis(
    database_path: Optional[PathLike] = None,
    output_dir: Optional[PathLike] = None,
) -> dict[str, object]:
    """Run every RCA method and write reproducible manager-ready outputs."""
    root = project_root()
    database = Path(database_path) if database_path else root / DEFAULT_DATABASE
    if not database.is_absolute():
        database = root / database
    if not database.exists():
        build_database(database)
    target = Path(output_dir) if output_dir else root / "data" / "processed"
    if not target.is_absolute():
        target = root / target
    target.mkdir(parents=True, exist_ok=True)

    routes = load_route_factors(database)
    exceptions = load_exception_facts(database)
    correlations = correlation_analysis(routes)
    segments = segmented_kpi_analysis(routes)
    thresholds = threshold_analysis(routes)
    trends = week_over_week_trends(database)
    rolling = rolling_average_analysis(database)
    anomalies = zscore_anomaly_detection(rolling)
    pareto = exception_pareto_analysis(exceptions)
    dsp_benchmark, station_benchmark = dsp_station_benchmarking(routes)
    summary = build_operational_insights_summary(
        routes, thresholds, segments, trends, anomalies, pareto,
        dsp_benchmark, station_benchmark,
    )

    outputs = {
        "correlation_analysis.csv": correlations,
        "segmented_kpi_analysis.csv": segments,
        "threshold_analysis.csv": thresholds,
        "week_over_week_trends.csv": trends,
        "rolling_average_analysis.csv": rolling,
        "zscore_anomalies.csv": anomalies,
        "exception_pareto_analysis.csv": pareto,
        "dsp_benchmark.csv": dsp_benchmark,
        "station_benchmark.csv": station_benchmark,
    }
    for filename, frame in outputs.items():
        frame.to_csv(target / filename, index=False)
    (target / "operational_insights_summary.md").write_text(summary, encoding="utf-8")
    manifest = {
        "analysis_period": {
            "start": str(pd.Timestamp(routes["service_date"].min()).date()),
            "end": str(pd.Timestamp(routes["service_date"].max()).date()),
        },
        "route_count": len(routes),
        "package_count": int(routes["package_records"].sum()),
        "output_row_counts": {filename: len(frame) for filename, frame in outputs.items()},
        "summary_file": "operational_insights_summary.md",
    }
    (target / "rca_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
