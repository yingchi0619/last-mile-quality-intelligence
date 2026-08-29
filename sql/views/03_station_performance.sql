-- Daily station scorecard, including regional rank and rolling operational KPIs.
CREATE OR REPLACE VIEW station_performance AS
WITH daily AS (
    SELECT
        service_date,
        station_id,
        station_name,
        region,
        market_type,
        COUNT(*) AS route_count,
        COUNT(DISTINCT driver_id) AS active_drivers,
        SUM(actual_packages) AS packages,
        SUM(on_time_packages)::DOUBLE / NULLIF(SUM(package_records), 0) AS on_time_delivery_rate,
        SUM(delivered_packages)::DOUBLE / NULLIF(SUM(package_records), 0) AS delivery_success_rate,
        SUM(pod_compliant_packages)::DOUBLE / NULLIF(SUM(delivered_packages), 0) AS pod_compliance_rate,
        SUM(exception_packages)::DOUBLE / NULLIF(SUM(package_records), 0) AS exception_rate,
        AVG(pickup_compliance_rate) AS pickup_compliance_rate,
        SUM(actual_packages)::DOUBLE / NULLIF(SUM(planned_capacity), 0) AS capacity_utilization,
        SUM(actual_packages)::DOUBLE / NULLIF(COUNT(DISTINCT driver_id), 0) AS packages_per_driver,
        AVG(pickup_delay_minutes) AS average_pickup_delay,
        LEAST(SUM(delivered_packages)::DOUBLE / NULLIF(SUM(planned_packages), 0), 1.0) AS route_completion_rate,
        AVG(driver_reliability) AS driver_reliability,
        AVG(route_density) AS average_route_density,
        SUM(actual_packages - planned_capacity) AS demand_capacity_gap
    FROM route_performance
    GROUP BY service_date, station_id, station_name, region, market_type
)
SELECT
    *,
    RANK() OVER (PARTITION BY service_date ORDER BY exception_rate DESC) AS daily_exception_rank,
    RANK() OVER (PARTITION BY service_date ORDER BY on_time_delivery_rate DESC) AS daily_otd_rank,
    AVG(on_time_delivery_rate) OVER (
        PARTITION BY station_id ORDER BY service_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7d_otd,
    AVG(exception_rate) OVER (
        PARTITION BY station_id ORDER BY service_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7d_exception_rate,
    SUM(demand_capacity_gap) OVER (
        PARTITION BY station_id ORDER BY service_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7d_demand_capacity_gap
FROM daily;
