-- Rank numeric operational factors by absolute correlation with failure and late outcomes.
WITH package_features AS (
    SELECT
        d.on_time_flag,
        CASE WHEN d.delivery_status = 'DELIVERED' THEN 0.0 ELSE 1.0 END AS failure_flag,
        r.capacity_utilization,
        r.pickup_delay_minutes,
        r.route_density,
        r.route_distance_miles,
        r.driver_reliability,
        r.planned_packages::DOUBLE AS planned_packages
    FROM deliveries d
    JOIN route_performance r USING (route_id)
), correlations AS (
    SELECT 'capacity_utilization' AS factor, CORR(capacity_utilization, 1 - on_time_flag) AS late_correlation, CORR(capacity_utilization, failure_flag) AS failure_correlation FROM package_features
    UNION ALL SELECT 'pickup_delay_minutes', CORR(pickup_delay_minutes, 1 - on_time_flag), CORR(pickup_delay_minutes, failure_flag) FROM package_features
    UNION ALL SELECT 'route_density', CORR(route_density, 1 - on_time_flag), CORR(route_density, failure_flag) FROM package_features
    UNION ALL SELECT 'route_distance_miles', CORR(route_distance_miles, 1 - on_time_flag), CORR(route_distance_miles, failure_flag) FROM package_features
    UNION ALL SELECT 'driver_reliability', CORR(driver_reliability, 1 - on_time_flag), CORR(driver_reliability, failure_flag) FROM package_features
    UNION ALL SELECT 'planned_packages', CORR(planned_packages, 1 - on_time_flag), CORR(planned_packages, failure_flag) FROM package_features
)
SELECT
    *,
    (ABS(late_correlation) + ABS(failure_correlation)) / 2 AS combined_absolute_correlation,
    RANK() OVER (ORDER BY (ABS(late_correlation) + ABS(failure_correlation)) / 2 DESC) AS influence_rank
FROM correlations
ORDER BY influence_rank;
