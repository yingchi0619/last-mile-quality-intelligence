"""Data-quality checks for generated relational tables."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import pandas as pd


@dataclass(frozen=True)
class ValidationReport:
    null_values: int
    duplicate_package_ids: int
    orphan_delivery_routes: int
    orphan_route_stations: int
    orphan_route_providers: int
    orphan_route_drivers: int
    route_package_count_mismatches: int

    @property
    def passed(self) -> bool:
        return all(value == 0 for value in asdict(self).values())


def validate_tables(tables: dict[str, pd.DataFrame]) -> ValidationReport:
    stations, providers = tables["stations"], tables["delivery_service_providers"]
    drivers, routes, deliveries = tables["drivers"], tables["routes"], tables["deliveries"]
    package_counts = deliveries.groupby("route_id").size()
    expected_counts = routes.set_index("route_id")["actual_packages"]
    aligned_counts = package_counts.reindex(expected_counts.index, fill_value=0)
    return ValidationReport(
        null_values=sum(int(frame.isna().sum().sum()) for frame in tables.values()),
        duplicate_package_ids=int(deliveries["package_id"].duplicated().sum()),
        orphan_delivery_routes=int((~deliveries["route_id"].isin(routes["route_id"])).sum()),
        orphan_route_stations=int((~routes["station_id"].isin(stations["station_id"])).sum()),
        orphan_route_providers=int((~routes["provider_id"].isin(providers["provider_id"])).sum()),
        orphan_route_drivers=int((~routes["driver_id"].isin(drivers["driver_id"])).sum()),
        route_package_count_mismatches=int((aligned_counts != expected_counts).sum()),
    )
