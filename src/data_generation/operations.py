"""Generate route and package facts with designed operational relationships."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import GenerationConfig, PROVIDER_PROFILES, STATION_PROFILES


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + np.exp(-value))


def _daily_route_target(service_date: pd.Timestamp, config: GenerationConfig, rng: np.random.Generator) -> tuple[int, bool, bool]:
    weekend = service_date.dayofweek >= 5
    peak_day = service_date.dayofweek in (0, 4) or service_date.day in (1, 15)
    base = int(rng.integers(config.min_routes_per_station_day, config.max_routes_per_station_day + 1))
    adjustment = (2 if peak_day else 0) - (2 if weekend else 0)
    return int(np.clip(base + adjustment, 10, 20)), weekend, peak_day


def _route_line_profiles(rng: np.random.Generator) -> dict[str, list[dict[str, object]]]:
    profiles: dict[str, list[dict[str, object]]] = {}
    for station in STATION_PROFILES:
        station_id = str(station["station_id"])
        line_count = int(station["route_line_count"])
        profiles[station_id] = [
            {
                "route_line_id": f"{station_id}-L{line_number:02d}",
                "density_modifier": float(np.clip(rng.normal(1.0, 0.10), 0.78, 1.22)),
                "distance_modifier": float(np.clip(rng.normal(1.0, 0.12), 0.75, 1.30)),
                "volume_modifier": float(np.clip(rng.normal(1.0, 0.09), 0.80, 1.20)),
            }
            for line_number in range(1, line_count + 1)
        ]
    return profiles


def generate_routes(config: GenerationConfig, drivers: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    dates = pd.date_range(config.start_date, periods=config.days, freq="D")
    station_lookup = {item["station_id"]: item for item in STATION_PROFILES}
    provider_lookup = {item["provider_id"]: item for item in PROVIDER_PROFILES}
    drivers_by_provider = {key: group.reset_index(drop=True) for key, group in drivers.groupby("provider_id")}
    provider_ids = list(provider_lookup)
    provider_weights = np.array([0.24, 0.26, 0.23, 0.27])
    route_lines_by_station = _route_line_profiles(rng)
    records: list[dict[str, object]] = []
    route_number = 1

    for day_index, service_date in enumerate(dates):
        for station_id, station in station_lookup.items():
            route_count, weekend, peak_day = _daily_route_target(service_date, config, rng)
            route_lines = route_lines_by_station[station_id]
            selected_indexes = rng.choice(len(route_lines), size=route_count, replace=route_count > len(route_lines))
            for line_index in selected_indexes:
                route_line = route_lines[int(line_index)]
                provider_id = str(rng.choice(provider_ids, p=provider_weights))
                provider = provider_lookup[provider_id]
                pool = drivers_by_provider[provider_id]
                weights = pool["historical_attendance_rate"].to_numpy()
                driver = pool.iloc[int(rng.choice(len(pool), p=weights / weights.sum()))]
                volume_factor = 1.12 if peak_day else (0.90 if weekend else 1.0)
                planned_packages = int(np.clip(rng.normal(50 * volume_factor * route_line["volume_modifier"], 8), 30, 78))
                planned_capacity = int(np.clip(planned_packages + rng.normal(8, 5), 38, 84))
                actual_packages = int(np.clip(round(planned_packages * rng.normal(1.01 if peak_day else 0.99, 0.07)), 26, 86))
                density = float(np.clip(rng.normal(station["density_mean"] * route_line["density_modifier"] * (0.94 if weekend else 1.0), 0.20), 0.55, 2.25))
                distance = float(np.clip(station["distance_mean"] * route_line["distance_modifier"] * (station["density_mean"] / density) + rng.normal(0, 6), 18, 110))
                utilization = actual_packages / planned_capacity
                base_delay = max(0.0, rng.normal(18, 20))
                late_arrival_shock = rng.gamma(shape=2.0, scale=26.0) if rng.random() < 0.12 else 0.0
                pickup_delay = max(
                    0.0,
                    base_delay
                    + late_arrival_shock
                    + max(utilization - 0.95, 0) * 65
                    + (12 if peak_day else 0)
                    - provider["quality_effect"] * 8,
                )
                anomaly_type = "NONE"
                if day_index == 21 and station_id == "EWR02":
                    pickup_delay += rng.uniform(70, 130)
                    anomaly_type = "STATION_SORT_DELAY"
                elif day_index in (56, 57) and provider_id == "DSP_GHI":
                    actual_packages = min(actual_packages + int(rng.integers(12, 22)), 82)
                    pickup_delay += rng.uniform(35, 80)
                    anomaly_type = "PROVIDER_CAPACITY_STRESS"
                elif day_index == 73 and station_id == "EWR03":
                    pickup_delay += rng.uniform(45, 100)
                    anomaly_type = "LOCAL_PROCESS_DISRUPTION"
                pickup_delay = min(pickup_delay, 240.0)
                planned_pickup = pd.Timestamp(service_date) + pd.Timedelta(hours=8)
                actual_pickup = planned_pickup + pd.Timedelta(minutes=float(pickup_delay))
                reliability = (float(driver["historical_attendance_rate"]) + float(driver["historical_delivery_success_rate"])) / 2
                records.append({
                    "route_id": f"R{route_number:06d}", "route_line_id": route_line["route_line_id"],
                    "service_date": service_date,
                    "station_id": station_id, "provider_id": provider_id, "driver_id": driver["driver_id"],
                    "planned_packages": planned_packages, "route_distance_miles": round(distance, 2),
                    "route_density": round(density, 3), "planned_capacity": planned_capacity,
                    "actual_packages": actual_packages, "planned_pickup_timestamp": planned_pickup,
                    "actual_pickup_timestamp": actual_pickup, "pickup_delay_minutes": round(pickup_delay, 2),
                    "station_effect_internal": station["quality_effect"], "provider_effect_internal": provider["quality_effect"],
                    "driver_reliability_internal": reliability, "is_weekend_internal": weekend, "is_peak_day_internal": peak_day,
                    "anomaly_type_internal": anomaly_type,
                })
                route_number += 1
    return pd.DataFrame(records)


def generate_deliveries(routes_internal: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    package_number = 1
    for route in routes_internal.itertuples(index=False):
        count = int(route.actual_packages)
        package_ids = [f"PKG{value:09d}" for value in range(package_number, package_number + count)]
        package_number += count
        utilization = route.actual_packages / route.planned_capacity
        on_time_score = (
            2.35 + 0.95 * (route.route_density - 1.25) - 2.35 * max(utilization - 0.92, 0)
            - 0.032 * route.pickup_delay_minutes + 5.2 * (route.driver_reliability_internal - 0.92)
            + route.station_effect_internal + route.provider_effect_internal - 0.18 * route.is_weekend_internal
            - 0.24 * route.is_peak_day_internal - (0.65 if route.anomaly_type_internal != "NONE" else 0.0)
        )
        success_score = (3.35 + 7.0 * (route.driver_reliability_internal - 0.93) + 0.45 * route.provider_effect_internal
                         + 0.25 * route.station_effect_internal - 0.75 * max(utilization - 1.0, 0)
                         - (0.28 if route.is_weekend_internal else 0.0))
        on_time_probability = float(np.clip(_sigmoid(on_time_score), 0.42, 0.985))
        success_probability = float(np.clip(_sigmoid(success_score), 0.82, 0.997))
        delivered = rng.random(count) < success_probability
        on_time = (rng.random(count) < on_time_probability) & delivered
        returned = (~delivered) & (rng.random(count) < 0.18)
        delivery_status = np.where(delivered, "DELIVERED", np.where(returned, "RETURNED", "FAILED"))
        pod_probability = np.clip(0.975 + 0.20 * (route.driver_reliability_internal - 0.95) + 0.008 * route.provider_effect_internal, 0.90, 0.995)
        pod_compliant = delivered & (rng.random(count) < pod_probability)
        pickup_base = pd.Timestamp(route.actual_pickup_timestamp)
        pickup_timestamps = pickup_base + pd.to_timedelta(rng.integers(0, 18, size=count), unit="m")
        route_hours = 3.2 + route.route_distance_miles / 22 + count / 18
        duration_minutes = np.maximum(30, np.sort(rng.uniform(0.12, 1.0, size=count)) * route_hours * 60 + rng.normal(0, 9, size=count))
        duration_minutes += np.where(on_time, 0, rng.uniform(35, 150, size=count))
        delivery_timestamps = pickup_base + pd.to_timedelta(duration_minutes, unit="m")
        exception_type = np.full(count, "NONE", dtype=object)
        exception_type[(~on_time) & delivered] = "LATE_DELIVERY"
        failed_mask = delivery_status == "FAILED"
        exception_type[failed_mask] = rng.choice(["ACCESS_ISSUE", "RECIPIENT_UNAVAILABLE", "PROCESS_EXCEPTION"], size=int(failed_mask.sum()), p=[0.38, 0.42, 0.20])
        exception_type[delivery_status == "RETURNED"] = "RETURN_TO_ORIGIN"
        if route.anomaly_type_internal != "NONE":
            exception_type[(~on_time) & (rng.random(count) < 0.55)] = route.anomaly_type_internal
        frames.append(pd.DataFrame({
            "package_id": package_ids, "route_id": route.route_id, "driver_id": route.driver_id,
            "service_date": route.service_date, "pickup_timestamp": pickup_timestamps,
            "delivery_timestamp": delivery_timestamps, "delivery_status": delivery_status,
            "on_time_flag": on_time.astype("int8"), "pod_compliant_flag": pod_compliant.astype("int8"),
            "exception_type": exception_type,
        }))
    return pd.concat(frames, ignore_index=True)


ROUTE_PUBLIC_COLUMNS = ["route_id", "route_line_id", "service_date", "station_id", "provider_id", "driver_id", "planned_packages", "route_distance_miles", "route_density", "planned_capacity", "actual_packages", "planned_pickup_timestamp", "actual_pickup_timestamp", "pickup_delay_minutes"]
