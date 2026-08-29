"""Week-over-week comparisons and rolling KPI trends."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import pandas as pd

from ..sql_runner import execute_query

PathLike = Union[str, Path]


def week_over_week_trends(database_path: Optional[PathLike] = None) -> pd.DataFrame:
    """Compare the latest seven days with the preceding 30-day baseline."""
    return execute_query(
        """
        WITH entity_daily AS (
            SELECT 'DSP' AS entity_type, provider_id AS entity_id, provider_name AS entity_name,
                   service_date, packages, on_time_delivery_rate, delivery_success_rate,
                   exception_rate, average_pickup_delay FROM dsp_performance
            UNION ALL
            SELECT 'STATION', station_id, station_name, service_date, packages,
                   on_time_delivery_rate, delivery_success_rate, exception_rate,
                   average_pickup_delay FROM station_performance
        ), bounds AS (SELECT MAX(service_date) AS max_date FROM entity_daily),
        summarized AS (
            SELECT entity_type, entity_id, entity_name,
                SUM(packages * on_time_delivery_rate) FILTER (WHERE service_date > max_date - INTERVAL 7 DAYS)
                    / NULLIF(SUM(packages) FILTER (WHERE service_date > max_date - INTERVAL 7 DAYS), 0) AS recent_7d_otd,
                SUM(packages * on_time_delivery_rate) FILTER (WHERE service_date > max_date - INTERVAL 37 DAYS AND service_date <= max_date - INTERVAL 7 DAYS)
                    / NULLIF(SUM(packages) FILTER (WHERE service_date > max_date - INTERVAL 37 DAYS AND service_date <= max_date - INTERVAL 7 DAYS), 0) AS prior_30d_otd,
                SUM(packages * delivery_success_rate) FILTER (WHERE service_date > max_date - INTERVAL 7 DAYS)
                    / NULLIF(SUM(packages) FILTER (WHERE service_date > max_date - INTERVAL 7 DAYS), 0) AS recent_7d_success,
                SUM(packages * delivery_success_rate) FILTER (WHERE service_date > max_date - INTERVAL 37 DAYS AND service_date <= max_date - INTERVAL 7 DAYS)
                    / NULLIF(SUM(packages) FILTER (WHERE service_date > max_date - INTERVAL 37 DAYS AND service_date <= max_date - INTERVAL 7 DAYS), 0) AS prior_30d_success,
                SUM(packages * exception_rate) FILTER (WHERE service_date > max_date - INTERVAL 7 DAYS)
                    / NULLIF(SUM(packages) FILTER (WHERE service_date > max_date - INTERVAL 7 DAYS), 0) AS recent_7d_exception_rate,
                SUM(packages * exception_rate) FILTER (WHERE service_date > max_date - INTERVAL 37 DAYS AND service_date <= max_date - INTERVAL 7 DAYS)
                    / NULLIF(SUM(packages) FILTER (WHERE service_date > max_date - INTERVAL 37 DAYS AND service_date <= max_date - INTERVAL 7 DAYS), 0) AS prior_30d_exception_rate,
                AVG(average_pickup_delay) FILTER (WHERE service_date > max_date - INTERVAL 7 DAYS) AS recent_7d_pickup_delay,
                AVG(average_pickup_delay) FILTER (WHERE service_date > max_date - INTERVAL 37 DAYS AND service_date <= max_date - INTERVAL 7 DAYS) AS prior_30d_pickup_delay
            FROM entity_daily CROSS JOIN bounds
            WHERE service_date > max_date - INTERVAL 37 DAYS
            GROUP BY entity_type, entity_id, entity_name
        )
        SELECT *,
            (recent_7d_otd - prior_30d_otd) * 100 AS otd_change_percentage_points,
            (recent_7d_success - prior_30d_success) * 100 AS success_change_percentage_points,
            (recent_7d_exception_rate - prior_30d_exception_rate) * 100 AS exception_change_percentage_points,
            recent_7d_pickup_delay - prior_30d_pickup_delay AS pickup_delay_change_minutes,
            RANK() OVER (PARTITION BY entity_type ORDER BY recent_7d_otd - prior_30d_otd) AS deterioration_rank
        FROM summarized ORDER BY entity_type, deterioration_rank
        """,
        database_path,
    )


def rolling_average_analysis(database_path: Optional[PathLike] = None) -> pd.DataFrame:
    """Return long-form daily 7- and 30-day rolling OTD by region, DSP, and station."""
    return execute_query(
        """
        WITH entity_daily AS (
            SELECT 'REGION' AS entity_type, 'REGION_ALL' AS entity_id, service_date,
                   packages, on_time_delivery_rate, exception_rate FROM daily_regional_performance
            UNION ALL
            SELECT 'DSP', provider_id, service_date, packages, on_time_delivery_rate, exception_rate FROM dsp_performance
            UNION ALL
            SELECT 'STATION', station_id, service_date, packages, on_time_delivery_rate, exception_rate FROM station_performance
        )
        SELECT *,
            AVG(on_time_delivery_rate) OVER (PARTITION BY entity_type, entity_id ORDER BY service_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS rolling_7d_otd,
            AVG(on_time_delivery_rate) OVER (PARTITION BY entity_type, entity_id ORDER BY service_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS rolling_30d_otd,
            AVG(exception_rate) OVER (PARTITION BY entity_type, entity_id ORDER BY service_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS rolling_7d_exception_rate
        FROM entity_daily ORDER BY entity_type, entity_id, service_date
        """,
        database_path,
    )
