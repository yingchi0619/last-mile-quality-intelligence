-- Which stations have the highest exception rate across the analysis period?
SELECT
    station_id,
    station_name,
    SUM(packages) AS packages,
    SUM(packages * exception_rate) / NULLIF(SUM(packages), 0) AS weighted_exception_rate,
    AVG(rolling_7d_exception_rate) AS average_rolling_7d_exception_rate,
    MAX(exception_rate) AS worst_daily_exception_rate,
    RANK() OVER (ORDER BY SUM(packages * exception_rate) / NULLIF(SUM(packages), 0) DESC) AS exception_rank
FROM station_performance
GROUP BY station_id, station_name
ORDER BY exception_rank;
