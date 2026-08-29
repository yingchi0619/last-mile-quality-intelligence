-- One row per route. This is the canonical KPI foundation for higher-level views.
CREATE OR REPLACE VIEW route_performance AS
WITH package_rollup AS (
    SELECT
        route_id,
        COUNT(*) AS package_records,
        COUNT(*) FILTER (WHERE delivery_status = 'DELIVERED') AS delivered_packages,
        COUNT(*) FILTER (WHERE delivery_status IN ('FAILED', 'RETURNED')) AS unsuccessful_packages,
        SUM(on_time_flag) AS on_time_packages,
        SUM(pod_compliant_flag) AS pod_compliant_packages,
        COUNT(*) FILTER (WHERE exception_type <> 'NONE') AS exception_packages,
        MAX(delivery_timestamp) AS route_last_delivery_timestamp
    FROM deliveries
    GROUP BY route_id
), route_base AS (
    SELECT
        r.*,
        s.station_name,
        s.region,
        s.market_type,
        p.provider_name,
        d.tenure_days,
        d.historical_attendance_rate,
        d.historical_delivery_success_rate,
        pr.package_records,
        pr.delivered_packages,
        pr.unsuccessful_packages,
        pr.on_time_packages,
        pr.pod_compliant_packages,
        pr.exception_packages,
        pr.route_last_delivery_timestamp,
        r.actual_packages::DOUBLE / NULLIF(r.planned_capacity, 0) AS capacity_utilization,
        (d.historical_attendance_rate + d.historical_delivery_success_rate) / 2.0 AS driver_reliability
    FROM routes r
    JOIN package_rollup pr USING (route_id)
    JOIN stations s USING (station_id)
    JOIN delivery_service_providers p USING (provider_id)
    JOIN drivers d USING (driver_id)
), route_kpis AS (
    SELECT
        *,
        on_time_packages::DOUBLE / NULLIF(package_records, 0) AS on_time_delivery_rate,
        delivered_packages::DOUBLE / NULLIF(package_records, 0) AS delivery_success_rate,
        pod_compliant_packages::DOUBLE / NULLIF(delivered_packages, 0) AS pod_compliance_rate,
        exception_packages::DOUBLE / NULLIF(package_records, 0) AS exception_rate,
        CASE WHEN pickup_delay_minutes <= 15 THEN 1.0 ELSE 0.0 END AS pickup_compliance_rate,
        LEAST(delivered_packages::DOUBLE / NULLIF(planned_packages, 0), 1.0) AS route_completion_rate,
        actual_packages::DOUBLE AS packages_per_driver,
        pickup_delay_minutes AS average_pickup_delay,
        route_density AS average_route_density
    FROM route_base
)
SELECT
    *,
    AVG(on_time_delivery_rate) OVER (
        PARTITION BY station_id, provider_id
        ORDER BY service_date
        RANGE BETWEEN INTERVAL 6 DAYS PRECEDING AND CURRENT ROW
    ) AS rolling_7d_route_otd,
    AVG(average_pickup_delay) OVER (
        PARTITION BY station_id, provider_id
        ORDER BY service_date
        RANGE BETWEEN INTERVAL 6 DAYS PRECEDING AND CURRENT ROW
    ) AS rolling_7d_pickup_delay,
    PERCENT_RANK() OVER (
        PARTITION BY station_id
        ORDER BY on_time_delivery_rate
    ) AS station_historical_otd_percentile,
    ROW_NUMBER() OVER (
        PARTITION BY station_id, provider_id, service_date
        ORDER BY on_time_delivery_rate DESC, route_id
    ) AS daily_route_rank
FROM route_kpis;
