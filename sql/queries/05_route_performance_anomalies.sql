-- Flag routes that materially underperform their station/DSP's preceding 30 routes.
WITH historical_baseline AS (
    SELECT
        *,
        AVG(on_time_delivery_rate) OVER (
            PARTITION BY station_id, provider_id
            ORDER BY service_date, route_id ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
        ) AS prior_30_route_otd,
        STDDEV_SAMP(on_time_delivery_rate) OVER (
            PARTITION BY station_id, provider_id
            ORDER BY service_date, route_id ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
        ) AS prior_30_route_otd_stddev,
        AVG(pickup_delay_minutes) OVER (
            PARTITION BY station_id, provider_id
            ORDER BY service_date, route_id ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
        ) AS prior_30_route_pickup_delay
    FROM route_performance
)
SELECT
    route_id,
    service_date,
    station_id,
    provider_id,
    driver_id,
    on_time_delivery_rate,
    prior_30_route_otd,
    (on_time_delivery_rate - prior_30_route_otd) / NULLIF(prior_30_route_otd_stddev, 0) AS otd_z_score,
    pickup_delay_minutes,
    prior_30_route_pickup_delay,
    capacity_utilization,
    route_density,
    RANK() OVER (ORDER BY (on_time_delivery_rate - prior_30_route_otd) / NULLIF(prior_30_route_otd_stddev, 0)) AS anomaly_severity_rank
FROM historical_baseline
WHERE prior_30_route_otd IS NOT NULL
  AND on_time_delivery_rate < prior_30_route_otd - GREATEST(2 * prior_30_route_otd_stddev, 0.10)
ORDER BY anomaly_severity_rank, service_date DESC;
