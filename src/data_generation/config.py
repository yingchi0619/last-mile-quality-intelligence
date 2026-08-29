"""Configuration for the reproducible synthetic delivery network."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GenerationConfig:
    """Controls the size, dates, and reproducibility of generated data."""

    seed: int = 20250317
    start_date: str = "2026-01-06"
    days: int = 90
    min_routes_per_station_day: int = 15
    max_routes_per_station_day: int = 25
    driver_count: int = 100
    output_dir: Path = Path("data/raw")


STATION_PROFILES = (
    {"station_id": "EWR01", "station_name": "EWR01 Operations Node", "region": "REGION_NORTH", "market_type": "URBAN_CORE", "quality_effect": 0.45, "density_mean": 1.65, "distance_mean": 42.0},
    {"station_id": "EWR02", "station_name": "EWR02 Operations Node", "region": "REGION_CENTRAL", "market_type": "SUBURBAN_RING", "quality_effect": -0.35, "density_mean": 1.12, "distance_mean": 61.0},
    {"station_id": "EWR03", "station_name": "EWR03 Operations Node", "region": "REGION_SOUTH", "market_type": "MIXED_MARKET", "quality_effect": 0.05, "density_mean": 1.35, "distance_mean": 53.0},
)

PROVIDER_PROFILES = (
    {"provider_id": "DSP_ABC", "provider_name": "DSP_ABC", "contracted_capacity": 1450, "driver_count": 24, "quality_effect": 0.30},
    {"provider_id": "DSP_DEF", "provider_name": "DSP_DEF", "contracted_capacity": 1550, "driver_count": 26, "quality_effect": 0.05},
    {"provider_id": "DSP_GHI", "provider_name": "DSP_GHI", "contracted_capacity": 1350, "driver_count": 23, "quality_effect": -0.55},
    {"provider_id": "DSP_JKL", "provider_name": "DSP_JKL", "contracted_capacity": 1600, "driver_count": 27, "quality_effect": 0.15},
)
