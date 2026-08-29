-- Quantify the relationship between pickup-delay severity and late/failed delivery.
WITH bucketed AS (
    SELECT
        CASE
            WHEN r.pickup_delay_minutes < 5 THEN '00_UNDER_5_MIN'
            WHEN r.pickup_delay_minutes < 15 THEN '01_5_TO_15_MIN'
            WHEN r.pickup_delay_minutes < 30 THEN '02_15_TO_30_MIN'
            ELSE '03_30_PLUS_MIN'
        END AS pickup_delay_bucket,
        d.on_time_flag,
        d.delivery_status,
        r.pickup_delay_minutes
    FROM deliveries d
    JOIN route_performance r USING (route_id)
)
SELECT
    pickup_delay_bucket,
    COUNT(*) AS packages,
    AVG(pickup_delay_minutes) AS average_pickup_delay,
    AVG(1 - on_time_flag) AS late_or_unsuccessful_rate,
    AVG(CASE WHEN delivery_status = 'DELIVERED' THEN 0.0 ELSE 1.0 END) AS failure_rate,
    RANK() OVER (ORDER BY AVG(1 - on_time_flag) DESC) AS late_risk_rank
FROM bucketed
GROUP BY pickup_delay_bucket
ORDER BY pickup_delay_bucket;
