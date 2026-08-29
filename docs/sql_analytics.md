# DuckDB SQL Analytics Layer

The analytical database is built from the five synthetic Parquet files by running:

```bash
python build_database.py
```

The resulting local database is `data/processed/last_mile_quality.duckdb`. Generated database files are reproducible and intentionally excluded from Git.

## KPI definitions

| KPI | Definition |
|---|---|
| On-Time Delivery Rate | On-time successfully delivered packages / package records |
| Delivery Success Rate | Delivered packages / package records |
| POD Compliance Rate | POD-compliant packages / delivered packages |
| Exception Rate | Packages with an exception other than `NONE` / package records |
| Pickup Compliance Rate | Routes with pickup delay at or below 15 minutes / routes |
| Capacity Utilization | Actual packages / planned capacity |
| Packages per Driver | Packages / distinct active drivers for the reporting grain |
| Average Pickup Delay | Mean route pickup delay in minutes |
| Route Completion Rate | Delivered packages / planned packages |
| Driver Reliability | Mean of historical attendance and historical delivery-success rates |
| Average Route Density | Mean synthetic route-density index |

Rates at DSP, station, and regional level use additive package numerators and denominators where applicable, rather than averaging route percentages. This prevents small routes from receiving the same weight as large routes.

## SQL organization

- `sql/00_load_tables.sql`: materializes the five Parquet sources and creates indexes.
- `sql/views/`: six reusable analytical views.
- `sql/queries/`: ten business-question queries.

The views use CTEs, conditional aggregation, joins, window functions, rolling seven-day metrics, rankings, prior-period comparisons, percentiles, and historical anomaly baselines.

## Python usage

```python
from src.analytics import execute_query, execute_sql_file

daily = execute_query("SELECT * FROM daily_regional_performance")
capacity = execute_sql_file("sql/queries/03_otd_by_capacity_threshold.sql")
```
