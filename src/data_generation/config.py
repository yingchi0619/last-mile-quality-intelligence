"""Configuration for the reproducible synthetic delivery network."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GenerationConfig:
    """Controls the size, dates, and reproducibility of generated data."""

    seed: int = 20250317
    start_date: str = "2025-01-06"
    days: int = 90
    min_routes_per_station_day: int = 15
    max_routes_per_station_day: int = 25
    driver_count: int = 100
    output_dir: Path = Path("data/raw")


STATION_PROFILES = (
    {"station_id": "STN_A", "station_name": "Aurora Node", "region": "REGION_NORTH", "market_type": "URBAN_CORE", "quality_effect": 0.45, "density_mean": 1.65, "distance_mean": 42.0},
    {"station_id": "STN_B", "station_name": "Beacon Node", "region": "REGION_CENTRAL", "market_type": "SUBURBAN_RING", "quality_effect": -0.35, "density_mean": 1.12, "distance_mean": 61.0},
    {"station_id": "STN_C", "station_name": "Cobalt Node", "region": "REGION_SOUTH", "market_type": "MIXED_MARKET", "quality_effect": 0.05, "density_mean": 1.35, "distance_mean": 53.0},
)

PROVIDER_PROFILES = (
    {"provider_id": "DSP_ALPHA", "provider_name": "Alpha Fleet Collective", "contracted_capacity": 1450, "driver_count": 24, "quality_effect": 0.30},
    {"provider_id": "DSP_BETA", "provider_name": "Beta Route Partners", "contracted_capacity": 1550, "driver_count": 26, "quality_effect": 0.05},
    {"provider_id": "DSP_GAMMA", "provider_name": "Gamma Transit Group", "contracted_capacity": 1350, "driver_count": 23, "quality_effect": -0.55},
    {"provider_id": "DSP_DELTA", "provider_name": "Delta Delivery Works", "contracted_capacity": 1600, "driver_count": 27, "quality_effect": 0.15},
)
