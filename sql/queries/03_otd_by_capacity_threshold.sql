-- How does OTD change once route utilization exceeds 90%, 100%, and 110%?
WITH thresholds(threshold_label, threshold_value) AS (
    VALUES ('OVER_90_PERCENT', 0.90), ('OVER_100_PERCENT', 1.00), ('OVER_110_PERCENT', 1.10)
)
SELECT
    t.threshold_label,
    t.threshold_value,
    COUNT(*) AS routes,
    SUM(r.actual_packages) AS packages,
    SUM(r.on_time_packages)::DOUBLE / NULLIF(SUM(r.package_records), 0) AS on_time_delivery_rate,
    SUM(r.exception_packages)::DOUBLE / NULLIF(SUM(r.package_records), 0) AS exception_rate,
    AVG(r.pickup_delay_minutes) AS average_pickup_delay,
    AVG(r.capacity_utilization) AS average_capacity_utilization
FROM route_performance r
CROSS JOIN thresholds t
WHERE r.capacity_utilization > t.threshold_value
GROUP BY t.threshold_label, t.threshold_value
ORDER BY t.threshold_value;
