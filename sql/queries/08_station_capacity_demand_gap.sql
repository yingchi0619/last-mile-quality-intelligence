-- Rank stations by absolute and percentage gap between planned capacity and demand.
WITH station_capacity AS (
    SELECT
        station_id,
        station_name,
        SUM(planned_capacity) AS planned_capacity,
        SUM(actual_packages) AS actual_demand,
        SUM(actual_packages - planned_capacity) AS net_demand_capacity_gap,
        SUM(ABS(actual_packages - planned_capacity)) AS absolute_route_level_gap,
        AVG(capacity_utilization) AS average_utilization
    FROM route_performance
    GROUP BY station_id, station_name
)
SELECT
    *,
    net_demand_capacity_gap::DOUBLE / NULLIF(planned_capacity, 0) AS net_gap_rate,
    absolute_route_level_gap::DOUBLE / NULLIF(planned_capacity, 0) AS absolute_gap_rate,
    RANK() OVER (ORDER BY absolute_route_level_gap DESC) AS capacity_gap_rank
FROM station_capacity
ORDER BY capacity_gap_rank;
