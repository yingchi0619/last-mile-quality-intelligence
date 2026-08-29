# Last-Mile Regional Quality Intelligence System

**最后一公里区域质量与数据智能系统**

A professional portfolio project for demonstrating data-informed decision-making in a fully fictional last-mile logistics environment.

## Project purpose

This project is designed to demonstrate capabilities in:

- Last-mile logistics operations
- SQL and Python analytics
- Operational KPI monitoring
- Root cause analysis
- Capacity planning
- Basic forecasting analysis
- Operational process improvement

The workflow uses Python, pandas, NumPy, DuckDB, SQL, Streamlit, Plotly, scikit-learn, and pytest. The current version includes a reproducible 90-day synthetic data generator. Dashboards, models, and formal analyses remain out of scope for this phase.

## Data ethics and scope

> “This project uses entirely synthetic data created for portfolio demonstration purposes. It does not contain proprietary, confidential, or operational data from any current or former employer.”

All future companies, stations, routes, service partners, drivers, geographies, and operational metrics in this repository must be fictional. Real company identifiers, station or route codes, ZIP codes, customer or driver information, prices, and internal operational information are prohibited.

## Repository structure

```text
last-mile-quality-intelligence/
├── app/                       # Future Streamlit application components
├── data/
│   ├── raw/                   # Future immutable synthetic source data
│   └── processed/             # Future cleaned and analysis-ready data
├── notebooks/                 # Future exploratory notebooks
├── sql/                       # DuckDB loading, views, and business queries
├── src/
│   ├── analytics/             # KPI and root-cause analysis modules
│   ├── data_generation/       # Reproducible synthetic-data generators
│   ├── models/                # Future forecasting/capacity-planning code
│   └── utils/                 # Shared configuration and helper functions
├── tests/                     # Automated tests
├── .gitignore
├── generate_data.py           # Synthetic-data generation entry point
├── build_database.py          # DuckDB analytical-layer build entry point
├── main.py                    # Environment smoke-check entry point
└── requirements.txt
```

## Quick start

Python 3.11 or newer is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
pytest
python generate_data.py
python build_database.py
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Current status

Synthetic data generation and a DuckDB SQL analytics layer are implemented for stations, providers, drivers, routes, and deliveries. The SQL layer includes six KPI views and ten business-question queries. Generated Parquet and DuckDB files are intentionally excluded from Git. No dashboard or machine-learning implementation is included at this stage.

## License

No license has been selected yet. All rights are reserved unless a license is added later.
