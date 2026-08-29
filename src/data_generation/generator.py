"""Orchestrate generation, validation, and Parquet export."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd

from .config import GenerationConfig
from .data_dictionary import build_data_dictionary
from .dimensions import generate_drivers, generate_providers, generate_stations
from .operations import ROUTE_PUBLIC_COLUMNS, generate_deliveries, generate_routes
from .validation import ValidationReport, validate_tables


def generate_all(config: Optional[GenerationConfig] = None) -> tuple[dict[str, pd.DataFrame], ValidationReport]:
    config = config or GenerationConfig()
    rng = np.random.default_rng(config.seed)
    stations, providers = generate_stations(), generate_providers()
    drivers = generate_drivers(config, rng)
    routes_internal = generate_routes(config, drivers, rng)
    deliveries = generate_deliveries(routes_internal, rng)
    tables = {"stations": stations, "delivery_service_providers": providers, "drivers": drivers,
              "routes": routes_internal.loc[:, ROUTE_PUBLIC_COLUMNS], "deliveries": deliveries}
    report = validate_tables(tables)
    if not report.passed:
        raise ValueError(f"Generated data failed validation: {asdict(report)}")
    return tables, report


def write_outputs(tables: dict[str, pd.DataFrame], output_dir: Path) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for table_name, frame in tables.items():
        frame.to_parquet(output_dir / f"{table_name}.parquet", index=False)
        counts[f"{table_name}.parquet"] = len(frame)
    dictionary = build_data_dictionary()
    dictionary.to_csv(output_dir / "data_dictionary.csv", index=False)
    counts["data_dictionary.csv"] = len(dictionary)
    return counts


def run_generation(config: Optional[GenerationConfig] = None) -> dict[str, object]:
    config = config or GenerationConfig()
    tables, report = generate_all(config)
    return {"table_counts": {name: len(frame) for name, frame in tables.items()},
            "file_counts": write_outputs(tables, config.output_dir),
            "date_min": str(tables["routes"]["service_date"].min().date()),
            "date_max": str(tables["routes"]["service_date"].max().date()),
            "validation": asdict(report)}
