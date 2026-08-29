-- Driver-level performance and within-DSP ranking across the full analysis period.
CREATE OR REPLACE VIEW driver_performance AS
WITH driver_rollup AS (
    SELECT
        driver_id,
        provider_id,
        provider_name,
        COUNT(*) AS route_count,
        COUNT(DISTINCT service_date) AS active_days,
        MIN(service_date) AS first_service_date,
        MAX(service_date) AS last_service_date,
        SUM(actual_packages) AS packages,
        SUM(on_time_packages)::DOUBLE / NULLIF(SUM(package_records), 0) AS on_time_delivery_rate,
        SUM(delivered_packages)::DOUBLE / NULLIF(SUM(package_records), 0) AS delivery_success_rate,
        SUM(pod_compliant_packages)::DOUBLE / NULLIF(SUM(delivered_packages), 0) AS pod_compliance_rate,
        SUM(exception_packages)::DOUBLE / NULLIF(SUM(package_records), 0) AS exception_rate,
        AVG(pickup_compliance_rate) AS pickup_compliance_rate,
        SUM(actual_packages)::DOUBLE / NULLIF(SUM(planned_capacity), 0) AS capacity_utilization,
        SUM(actual_packages)::DOUBLE / NULLIF(COUNT(DISTINCT service_date), 0) AS packages_per_driver,
        AVG(pickup_delay_minutes) AS average_pickup_delay,
        LEAST(SUM(delivered_packages)::DOUBLE / NULLIF(SUM(planned_packages), 0), 1.0) AS route_completion_rate,
        MAX(driver_reliability) AS driver_reliability,
        AVG(route_density) AS average_route_density
    FROM route_performance
    GROUP BY driver_id, provider_id, provider_name
)
SELECT
    *,
    RANK() OVER (PARTITION BY provider_id ORDER BY on_time_delivery_rate DESC) AS dsp_otd_rank,
    PERCENT_RANK() OVER (ORDER BY on_time_delivery_rate) AS regional_otd_percentile,
    NTILE(4) OVER (ORDER BY driver_reliability) AS reliability_quartile,
    on_time_delivery_rate - AVG(on_time_delivery_rate) OVER (PARTITION BY provider_id) AS otd_vs_dsp_average
FROM driver_rollup;
