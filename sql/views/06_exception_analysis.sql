-- Daily exception mix with contribution, rolling trend, and severity ranking.
CREATE OR REPLACE VIEW exception_analysis AS
WITH exception_daily AS (
    SELECT
        d.service_date,
        r.station_id,
        r.station_name,
        r.provider_id,
        r.provider_name,
        d.exception_type,
        COUNT(*) AS exception_packages,
        COUNT(*) FILTER (WHERE d.delivery_status IN ('FAILED', 'RETURNED')) AS unsuccessful_packages,
        COUNT(*) FILTER (WHERE d.on_time_flag = 0) AS late_or_unsuccessful_packages
    FROM deliveries d
    JOIN route_performance r USING (route_id)
    WHERE d.exception_type <> 'NONE'
    GROUP BY d.service_date, r.station_id, r.station_name,
             r.provider_id, r.provider_name, d.exception_type
), with_totals AS (
    SELECT
        *,
        SUM(exception_packages) OVER (PARTITION BY service_date, station_id) AS station_daily_exceptions,
        SUM(exception_packages) OVER (PARTITION BY service_date) AS regional_daily_exceptions,
        RANK() OVER (PARTITION BY service_date ORDER BY exception_packages DESC) AS daily_exception_volume_rank,
        AVG(exception_packages) OVER (
            PARTITION BY station_id, provider_id, exception_type
            ORDER BY service_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS rolling_7d_exception_packages
    FROM exception_daily
)
SELECT
    *,
    exception_packages::DOUBLE / NULLIF(station_daily_exceptions, 0) AS station_exception_mix_rate,
    exception_packages::DOUBLE / NULLIF(regional_daily_exceptions, 0) AS regional_exception_contribution
FROM with_totals;
