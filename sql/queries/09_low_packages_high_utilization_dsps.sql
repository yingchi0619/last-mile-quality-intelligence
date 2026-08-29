-- Identify DSPs with low packages per active driver but above-median utilization.
WITH dsp_summary AS (
    SELECT
        provider_id,
        provider_name,
        SUM(packages)::DOUBLE / NULLIF(SUM(active_drivers), 0) AS packages_per_driver,
        SUM(packages * capacity_utilization) / NULLIF(SUM(packages), 0) AS weighted_utilization,
        SUM(packages * on_time_delivery_rate) / NULLIF(SUM(packages), 0) AS weighted_otd,
        AVG(average_pickup_delay) AS average_pickup_delay
    FROM dsp_performance
    GROUP BY provider_id, provider_name
), benchmarks AS (
    SELECT
        MEDIAN(packages_per_driver) AS median_packages_per_driver,
        MEDIAN(weighted_utilization) AS median_utilization
    FROM dsp_summary
)
SELECT
    d.*,
    b.median_packages_per_driver,
    b.median_utilization,
    CASE
        WHEN d.packages_per_driver < b.median_packages_per_driver
         AND d.weighted_utilization > b.median_utilization
        THEN 1 ELSE 0
    END AS low_packages_high_utilization_flag,
    RANK() OVER (ORDER BY d.weighted_utilization DESC, d.packages_per_driver) AS inefficiency_rank
FROM dsp_summary d
CROSS JOIN benchmarks b
ORDER BY low_packages_high_utilization_flag DESC, inefficiency_rank;
