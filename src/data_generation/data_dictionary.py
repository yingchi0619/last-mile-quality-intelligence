"""Machine-readable data dictionary for all synthetic tables."""

import pandas as pd

FIELDS = [
    ("stations", "station_id", "string", "Unique fictional station identifier", "EWR01"),
    ("stations", "station_name", "string", "Fictional station display name", "EWR01 Operations Node"),
    ("stations", "region", "string", "Fictional operating region", "REGION_NORTH"),
    ("stations", "market_type", "string", "Synthetic market classification", "URBAN_CORE"),
    ("delivery_service_providers", "provider_id", "string", "Unique fictional provider identifier", "DSP_ABC"),
    ("delivery_service_providers", "provider_name", "string", "Fictional provider display name", "DSP_ABC"),
    ("delivery_service_providers", "contracted_capacity", "int64", "Synthetic daily package capacity", "1450"),
    ("delivery_service_providers", "active_drivers", "int64", "Number of active synthetic drivers", "24"),
    ("drivers", "driver_id", "string", "Unique fictional driver identifier", "DRV0001"),
    ("drivers", "provider_id", "string", "Provider employing the synthetic driver", "DSP_ABC"),
    ("drivers", "tenure_days", "int64", "Synthetic driver tenure in days", "365"),
    ("drivers", "historical_attendance_rate", "float64", "Generated historical attendance proportion", "0.9625"),
    ("drivers", "historical_delivery_success_rate", "float64", "Generated historical delivery success proportion", "0.9712"),
    ("routes", "route_id", "string", "Unique fictional route identifier", "R000001"),
    ("routes", "service_date", "date", "Synthetic route operating date", "2026-01-06"),
    ("routes", "station_id", "string", "Origin station identifier", "EWR01"),
    ("routes", "provider_id", "string", "Assigned provider identifier", "DSP_ABC"),
    ("routes", "driver_id", "string", "Assigned driver identifier", "DRV0001"),
    ("routes", "planned_packages", "int64", "Packages expected during planning", "46"),
    ("routes", "route_distance_miles", "float64", "Synthetic planned route distance", "42.75"),
    ("routes", "route_density", "float64", "Synthetic stops/packages concentration index", "1.650"),
    ("routes", "planned_capacity", "int64", "Maximum planned package capacity", "52"),
    ("routes", "actual_packages", "int64", "Package records actually assigned", "48"),
    ("routes", "pickup_delay_minutes", "float64", "Minutes after planned pickup time", "7.50"),
    ("deliveries", "package_id", "string", "Unique fictional package identifier", "PKG000000001"),
    ("deliveries", "route_id", "string", "Associated fictional route identifier", "R000001"),
    ("deliveries", "driver_id", "string", "Associated fictional driver identifier", "DRV0001"),
    ("deliveries", "service_date", "date", "Synthetic service date", "2026-01-06"),
    ("deliveries", "pickup_timestamp", "timestamp", "Synthetic package pickup timestamp", "2026-01-06 08:12:00"),
    ("deliveries", "delivery_timestamp", "timestamp", "Synthetic delivery or final-attempt timestamp", "2026-01-06 14:26:00"),
    ("deliveries", "delivery_status", "string", "Synthetic final package outcome", "DELIVERED"),
    ("deliveries", "on_time_flag", "int8", "1 when successfully delivered on time", "1"),
    ("deliveries", "pod_compliant_flag", "int8", "1 when proof-of-delivery is compliant", "1"),
    ("deliveries", "exception_type", "string", "Synthetic exception category or NONE", "LATE_DELIVERY"),
]


def build_data_dictionary() -> pd.DataFrame:
    return pd.DataFrame(FIELDS, columns=["table_name", "field_name", "data_type", "description", "example_value"])
