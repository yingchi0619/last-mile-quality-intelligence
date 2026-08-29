-- Which DSPs persistently underperform the package-weighted regional OTD benchmark?
WITH consistency AS (
    SELECT
        provider_id,
        provider_name,
        COUNT(*) AS observed_days,
        SUM(below_region_flag) AS days_below_region,
        AVG(on_time_delivery_rate) AS average_otd,
        AVG(regional_otd_rate) AS average_regional_otd,
        AVG(otd_vs_region) AS average_gap_to_region,
        AVG(exception_rate) AS average_exception_rate
    FROM dsp_performance
    GROUP BY provider_id, provider_name
)
SELECT
    *,
    days_below_region::DOUBLE / observed_days AS share_days_below_region,
    RANK() OVER (ORDER BY days_below_region::DOUBLE / observed_days DESC, average_gap_to_region) AS persistence_rank
FROM consistency
WHERE days_below_region::DOUBLE / observed_days >= 0.60
ORDER BY persistence_rank;
