"""Shared KPI and root-cause factor definitions."""

NUMERIC_FACTORS = [
    "pickup_delay_minutes",
    "capacity_utilization",
    "route_density",
    "route_distance_miles",
    "package_volume",
    "driver_reliability",
]

OUTCOME_METRICS = [
    "on_time_delivery_rate",
    "delivery_success_rate",
    "exception_rate",
]

RATE_NUMERATORS = {
    "on_time_delivery_rate": "on_time_packages",
    "delivery_success_rate": "delivered_packages",
    "exception_rate": "exception_packages",
}
