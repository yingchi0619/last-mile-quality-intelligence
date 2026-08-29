"""Generate fictional station, provider, and driver dimension tables."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import GenerationConfig, PROVIDER_PROFILES, STATION_PROFILES


def generate_stations() -> pd.DataFrame:
    public_fields = ("station_id", "station_name", "region", "market_type")
    return pd.DataFrame(STATION_PROFILES).loc[:, public_fields]


def generate_providers() -> pd.DataFrame:
    return pd.DataFrame([
        {"provider_id": p["provider_id"], "provider_name": p["provider_name"], "contracted_capacity": p["contracted_capacity"], "active_drivers": p["driver_count"]}
        for p in PROVIDER_PROFILES
    ])


def generate_drivers(config: GenerationConfig, rng: np.random.Generator) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    driver_number = 1
    for profile in PROVIDER_PROFILES:
        for _ in range(profile["driver_count"]):
            tenure = int(np.clip(rng.gamma(shape=2.5, scale=150), 14, 1_400))
            experience_boost = min(tenure / 1_400, 1.0) * 0.018
            attendance = np.clip(0.935 + profile["quality_effect"] * 0.012 + experience_boost + rng.normal(0, 0.025), 0.82, 0.995)
            success = np.clip(0.945 + profile["quality_effect"] * 0.014 + experience_boost + rng.normal(0, 0.018), 0.86, 0.995)
            records.append({
                "driver_id": f"DRV{driver_number:04d}",
                "provider_id": profile["provider_id"],
                "tenure_days": tenure,
                "historical_attendance_rate": round(float(attendance), 4),
                "historical_delivery_success_rate": round(float(success), 4),
            })
            driver_number += 1
    drivers = pd.DataFrame(records)
    if len(drivers) != config.driver_count:
        raise ValueError("Configured driver count does not match provider allocation.")
    return drivers
