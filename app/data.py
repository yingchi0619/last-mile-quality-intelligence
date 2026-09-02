"""Cached data access for the Streamlit dashboard."""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

from src.analytics import build_database, execute_query
from src.analytics.database import DEFAULT_DATABASE, project_root
from src.analytics.rca import run_root_cause_analysis
from src.analytics.rca.data_access import load_route_factors
from src.analytics.capacity_simulation import CapacityAllocationSimulator
from src.models.pipeline import run_late_delivery_model


@st.cache_resource(show_spinner=False)
def database_path() -> Path:
    path = project_root() / DEFAULT_DATABASE
    return path if path.exists() else build_database(path)


@st.cache_data(show_spinner=False)
def route_data() -> pd.DataFrame:
    frame = execute_query(
        """
        SELECT route_id, route_line_id, service_date, station_id, station_name, provider_id,
               provider_name, driver_id, planned_packages, planned_capacity,
               actual_packages, route_distance_miles, route_density,
               planned_pickup_timestamp, actual_pickup_timestamp,
               pickup_delay_minutes, capacity_utilization, driver_reliability,
               package_records, delivered_packages, on_time_packages,
               pod_compliant_packages, exception_packages,
               on_time_delivery_rate, delivery_success_rate,
               pod_compliance_rate, exception_rate
        FROM route_performance ORDER BY service_date, route_id
        """,
        database_path(),
    )
    frame["service_date"] = pd.to_datetime(frame["service_date"])
    frame["planned_pickup_timestamp"] = pd.to_datetime(frame["planned_pickup_timestamp"])
    frame["actual_pickup_timestamp"] = pd.to_datetime(frame["actual_pickup_timestamp"])
    return frame


@st.cache_data(show_spinner=False)
def daily_data() -> pd.DataFrame:
    frame = execute_query("SELECT * FROM daily_regional_performance ORDER BY service_date", database_path())
    frame["service_date"] = pd.to_datetime(frame["service_date"])
    return frame


@st.cache_data(show_spinner=False)
def processed_csv(filename: str) -> pd.DataFrame:
    path = project_root() / "data" / "processed" / filename
    if not path.exists():
        run_root_cause_analysis()
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def risk_scores() -> pd.DataFrame:
    path = project_root() / "data" / "processed" / "late_delivery_model" / "route_risk_scores.parquet"
    if not path.exists():
        run_late_delivery_model()
    frame = pd.read_parquet(path)
    frame["service_date"] = pd.to_datetime(frame["service_date"])
    return frame


@st.cache_resource(show_spinner=False)
def selected_risk_model():
    path = project_root() / "data" / "processed" / "late_delivery_model" / "selected_late_delivery_model.joblib"
    if not path.exists():
        run_late_delivery_model()
    return joblib.load(path)


@st.cache_resource(show_spinner=False)
def capacity_simulator() -> CapacityAllocationSimulator:
    return CapacityAllocationSimulator(load_route_factors(database_path()))


@st.cache_data(show_spinner=False)
def model_metrics() -> pd.DataFrame:
    path = project_root() / "data" / "processed" / "late_delivery_model" / "model_metrics.csv"
    if not path.exists():
        run_late_delivery_model()
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def feature_importance() -> pd.DataFrame:
    path = project_root() / "data" / "processed" / "late_delivery_model" / "feature_importance.csv"
    if not path.exists():
        run_late_delivery_model()
    return pd.read_csv(path)
