-- Regional daily KPI trend with 7-day rolling averages and prior-week comparisons.
CREATE OR REPLACE VIEW daily_regional_performance AS
WITH daily AS (
    SELECT
        service_date,
        COUNT(*) AS route_count,
        COUNT(DISTINCT station_id) AS active_stations,
        COUNT(DISTINCT provider_id) AS active_dsps,
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
        AVG(route_density) AS average_route_density
    FROM route_performance
    GROUP BY service_date
)
SELECT
    *,
    AVG(on_time_delivery_rate) OVER (ORDER BY service_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS rolling_7d_otd,
    AVG(delivery_success_rate) OVER (ORDER BY service_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS rolling_7d_delivery_success,
    AVG(exception_rate) OVER (ORDER BY service_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS rolling_7d_exception_rate,
    AVG(capacity_utilization) OVER (ORDER BY service_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS rolling_7d_utilization,
    on_time_delivery_rate - LAG(on_time_delivery_rate, 7) OVER (ORDER BY service_date) AS otd_week_over_week_change,
    exception_rate - LAG(exception_rate, 7) OVER (ORDER BY service_date) AS exception_week_over_week_change,
    DENSE_RANK() OVER (ORDER BY on_time_delivery_rate) AS worst_otd_day_rank
FROM daily;
