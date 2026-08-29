-- Daily DSP scorecard with regional benchmark, trend, and ranking windows.
CREATE OR REPLACE VIEW dsp_performance AS
WITH daily AS (
    SELECT
        service_date,
        provider_id,
        provider_name,
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
        AVG(route_density) AS average_route_density
    FROM route_performance
    GROUP BY service_date, provider_id, provider_name
), benchmarked AS (
    SELECT
        *,
        SUM(packages * on_time_delivery_rate) OVER (PARTITION BY service_date)
            / NULLIF(SUM(packages) OVER (PARTITION BY service_date), 0) AS regional_otd_rate,
        RANK() OVER (PARTITION BY service_date ORDER BY on_time_delivery_rate DESC) AS daily_otd_rank,
        AVG(on_time_delivery_rate) OVER (
            PARTITION BY provider_id ORDER BY service_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS rolling_7d_otd,
        AVG(exception_rate) OVER (
            PARTITION BY provider_id ORDER BY service_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS rolling_7d_exception_rate,
        LAG(on_time_delivery_rate, 7) OVER (
            PARTITION BY provider_id ORDER BY service_date
        ) AS otd_7_days_ago
    FROM daily
)
SELECT
    *,
    on_time_delivery_rate - regional_otd_rate AS otd_vs_region,
    rolling_7d_otd - otd_7_days_ago AS rolling_7d_otd_change,
    CASE WHEN on_time_delivery_rate < regional_otd_rate THEN 1 ELSE 0 END AS below_region_flag
FROM benchmarked;
