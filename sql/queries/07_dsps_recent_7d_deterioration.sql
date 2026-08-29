-- Compare each DSP's latest seven days with the immediately preceding seven days.
WITH bounds AS (
    SELECT MAX(service_date) AS max_date FROM dsp_performance
), periodized AS (
    SELECT
        d.provider_id,
        d.provider_name,
        CASE
            WHEN d.service_date > b.max_date - INTERVAL 7 DAYS THEN 'RECENT_7D'
            WHEN d.service_date > b.max_date - INTERVAL 14 DAYS THEN 'PRIOR_7D'
        END AS period,
        d.on_time_delivery_rate,
        d.exception_rate,
        d.average_pickup_delay
    FROM dsp_performance d
    CROSS JOIN bounds b
    WHERE d.service_date > b.max_date - INTERVAL 14 DAYS
), comparison AS (
    SELECT
        provider_id,
        provider_name,
        AVG(on_time_delivery_rate) FILTER (WHERE period = 'RECENT_7D') AS recent_7d_otd,
        AVG(on_time_delivery_rate) FILTER (WHERE period = 'PRIOR_7D') AS prior_7d_otd,
        AVG(exception_rate) FILTER (WHERE period = 'RECENT_7D') AS recent_7d_exception_rate,
        AVG(exception_rate) FILTER (WHERE period = 'PRIOR_7D') AS prior_7d_exception_rate,
        AVG(average_pickup_delay) FILTER (WHERE period = 'RECENT_7D') AS recent_7d_pickup_delay,
        AVG(average_pickup_delay) FILTER (WHERE period = 'PRIOR_7D') AS prior_7d_pickup_delay
    FROM periodized
    GROUP BY provider_id, provider_name
)
SELECT
    *,
    recent_7d_otd - prior_7d_otd AS otd_change,
    recent_7d_exception_rate - prior_7d_exception_rate AS exception_rate_change,
    recent_7d_pickup_delay - prior_7d_pickup_delay AS pickup_delay_change,
    RANK() OVER (ORDER BY recent_7d_otd - prior_7d_otd) AS deterioration_rank
FROM comparison
WHERE recent_7d_otd < prior_7d_otd
ORDER BY deterioration_rank;
