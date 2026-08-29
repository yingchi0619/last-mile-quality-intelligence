"""Load analysis-ready frames from the DuckDB analytical layer."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import pandas as pd

from ..sql_runner import execute_query

PathLike = Union[str, Path]


def load_route_factors(database_path: Optional[PathLike] = None) -> pd.DataFrame:
    """Load one row per route with explanatory factors and KPI components."""
    return execute_query(
        """
        SELECT
            route_id,
            service_date,
            station_id,
            station_name,
            provider_id,
            provider_name,
            driver_id,
            STRFTIME(service_date, '%A') AS day_of_week,
            pickup_delay_minutes,
            planned_capacity,
            capacity_utilization,
            route_density,
            route_distance_miles,
            actual_packages AS package_volume,
            driver_reliability,
            package_records,
            on_time_packages,
            delivered_packages,
            exception_packages,
            on_time_delivery_rate,
            delivery_success_rate,
            exception_rate
        FROM route_performance
        ORDER BY service_date, route_id
        """,
        database_path,
    )


def load_exception_facts(database_path: Optional[PathLike] = None) -> pd.DataFrame:
    return execute_query(
        """
        SELECT
            d.service_date,
            r.station_id,
            r.station_name,
            r.provider_id,
            r.provider_name,
            d.exception_type
        FROM deliveries d
        JOIN route_performance r USING (route_id)
        WHERE d.exception_type <> 'NONE'
        """,
        database_path,
    )
