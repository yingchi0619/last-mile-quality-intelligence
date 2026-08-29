# Operational Root Cause Analysis

Run the complete workflow with:

```bash
python run_root_cause_analysis.py
```

The workflow reads the DuckDB analytical layer and writes reproducible outputs to `data/processed/`.

## Methods

- **Correlation analysis:** Pearson and Spearman relationships between numeric operational factors and route-level OTD, delivery success, and exception rate.
- **Segmented KPI analysis:** Package-weighted KPIs across factor terciles, DSPs, stations, and days of week.
- **Threshold analysis:** Evaluates observed factor quantiles and selects the breakpoint with the largest supported OTD deterioration while enforcing minimum sample sizes.
- **Week-over-week analysis:** Compares the latest seven days with the immediately preceding 30-day baseline for every DSP and station.
- **Rolling averages:** Seven- and 30-day OTD plus seven-day exception trends for region, DSP, and station.
- **Z-score anomalies:** Flags daily OTD drops and exception spikes relative to each entity's preceding 28 observations.
- **Exception Pareto:** Ranks exception categories and calculates cumulative contribution.
- **Benchmarking:** Package-weighted DSP and station rankings against the regional result.

## Outputs

- `correlation_analysis.csv`
- `segmented_kpi_analysis.csv`
- `threshold_analysis.csv`
- `week_over_week_trends.csv`
- `rolling_average_analysis.csv`
- `zscore_anomalies.csv`
- `exception_pareto_analysis.csv`
- `dsp_benchmark.csv`
- `station_benchmark.csv`
- `operational_insights_summary.md`
- `rca_manifest.json`

The narrative summary contains only values calculated during the current run. It is written for regional operating review and intentionally distinguishes observed associations from proven causation.
