-- Compare package-weighted OTD across operationally meaningful density buckets.
WITH density_buckets AS (
    SELECT
        CASE
            WHEN route_density < 0.90 THEN '01_VERY_LOW'
            WHEN route_density < 1.20 THEN '02_LOW'
            WHEN route_density < 1.50 THEN '03_MEDIUM'
            WHEN route_density < 1.80 THEN '04_HIGH'
            ELSE '05_VERY_HIGH'
        END AS density_bucket,
        *
    FROM route_performance
)
SELECT
    density_bucket,
    COUNT(*) AS routes,
    SUM(actual_packages) AS packages,
    AVG(route_density) AS average_route_density,
    SUM(on_time_packages)::DOUBLE / NULLIF(SUM(package_records), 0) AS on_time_delivery_rate,
    SUM(exception_packages)::DOUBLE / NULLIF(SUM(package_records), 0) AS exception_rate,
    AVG(pickup_delay_minutes) AS average_pickup_delay,
    RANK() OVER (ORDER BY SUM(on_time_packages)::DOUBLE / NULLIF(SUM(package_records), 0)) AS worst_otd_rank
FROM density_buckets
GROUP BY density_bucket
ORDER BY density_bucket;
