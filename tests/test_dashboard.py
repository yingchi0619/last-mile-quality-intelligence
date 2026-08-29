"""Smoke tests for all Streamlit dashboard pages and shared transformations."""

from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from app.data import route_data
from app.utils import aggregate_kpis, grouped_performance


APP_PATH = Path(__file__).resolve().parents[1] / "app" / "app.py"


def test_dashboard_all_pages_render_without_exceptions() -> None:
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    assert not app.exception
    for page in [
        "02  Station & DSP Performance",
        "03  Root Cause Analysis",
        "04  Capacity Planning",
        "05  Route Risk",
    ]:
        app.radio[0].set_value(page)
        app.run(timeout=30)
        assert not app.exception, f"Dashboard page failed: {page}"


def test_dashboard_kpis_are_bounded_and_nonempty() -> None:
    routes = route_data()
    kpis = aggregate_kpis(routes.tail(500))
    for metric in ["otd", "success", "pod", "exception", "utilization"]:
        assert 0 <= kpis[metric] <= 1.3
    assert kpis["packages_per_driver"] > 0
    grouped = grouped_performance(routes, ["provider_id"])
    assert len(grouped) == 4
    assert grouped[["otd", "success", "exception_rate"]].notna().all().all()
