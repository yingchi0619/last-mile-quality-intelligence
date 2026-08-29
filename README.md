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

The workflow uses Python, pandas, NumPy, DuckDB, SQL, Streamlit, Plotly, scikit-learn, and pytest. The current version includes a reproducible 90-day synthetic data generator, analytical views, operational diagnosis, capacity scenario planning, route-risk modeling, and a five-page leadership dashboard.

## Data ethics and scope

> “This project uses entirely synthetic data created for portfolio demonstration purposes. It does not contain proprietary, confidential, or operational data from any current or former employer.”

All future companies, stations, routes, service partners, drivers, geographies, and operational metrics in this repository must be fictional. Real company identifiers, station or route codes, ZIP codes, customer or driver information, prices, and internal operational information are prohibited.

## Repository structure

```text
last-mile-quality-intelligence/
├── app/                       # Modular Streamlit application, pages, components, and styles
├── data/
│   ├── raw/                   # Future immutable synthetic source data
│   └── processed/             # Future cleaned and analysis-ready data
├── notebooks/                 # Future exploratory notebooks
├── sql/                       # DuckDB loading, views, and business queries
├── src/
│   ├── analytics/             # KPI and root-cause analysis modules
│   ├── data_generation/       # Reproducible synthetic-data generators
│   ├── models/                # Prototype pre-dispatch route-risk modeling
│   └── utils/                 # Shared configuration and helper functions
├── tests/                     # Automated tests
├── .gitignore
├── generate_data.py           # Synthetic-data generation entry point
├── build_database.py          # DuckDB analytical-layer build entry point
├── run_root_cause_analysis.py # Operational RCA and insight-generation entry point
├── run_capacity_simulation.py # DSP volume-allocation scenario entry point
├── run_late_delivery_model.py # Prototype route-risk training entry point
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
python run_root_cause_analysis.py
python run_capacity_simulation.py
python run_late_delivery_model.py
streamlit run app/app.py
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Operations intelligence dashboard

Launch the application from the repository root:

```bash
source .venv/bin/activate
streamlit run app/app.py
```

The dashboard provides five coordinated workflows:

- **Executive Overview** — leadership KPIs, rolling OTD trend, station ranking, DSP leaderboard, and capacity-versus-quality analysis.
- **Station & DSP Performance** — provider drill-down, configurable operating trends, and route-level execution detail.
- **Root Cause Analysis** — dynamic diagnostic findings, threshold analysis, exception Pareto, and anomaly alerts.
- **Capacity Planning** — interactive source/receiver DSP reallocation scenarios with before-versus-after estimates.
- **Route Risk** — scored holdout routes, risk drivers, distribution, and compact model diagnostics.

The UI uses shared cards, filter controls, chart styling, status logic, and cached data/model resources. It is optimized for desktop and laptop layouts.

## Current status

Synthetic data generation, the DuckDB SQL analytics layer, modular operational root-cause analysis, capacity-allocation simulation, route-risk prototypes, and the Streamlit operations intelligence dashboard are implemented. Generated data, databases, model artifacts, and analysis outputs are intentionally excluded from Git and can be reproduced with the commands above.

> “A prototype demonstrating how pre-dispatch operational signals can be used to identify potentially high-risk routes.”

The Late Delivery Risk Model compares Logistic Regression and Random Forest using chronological validation and holdout periods. It explicitly remains a portfolio prototype—not production-ready AI.

## License

No license has been selected yet. All rights are reserved unless a license is added later.
