"""Executive Overview page."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.components.charts import horizontal_rank, scatter_capacity, style_figure, trend_chart
from app.components.filter_bar import apply_filters, filter_bar
from app.components.kpi_card import kpi_card
from app.components.status_badge import operational_status
from app.components.theme import page_header, section_header
from app.utils import aggregate_kpis, daily_performance, grouped_performance, prior_period


def render(routes: pd.DataFrame) -> None:
    latest = routes["service_date"].max().strftime("%b %d, %Y")
    page_header("Regional Performance Overview", "Monitor delivery quality, capacity health and network performance.", latest)
    filters = filter_bar(routes, "exec", 30)
    current = apply_filters(routes, filters)
    if current.empty:
        st.info("No operating records match the selected filters. Reset filters to restore the network view.")
        return
    prior = prior_period(routes, current)
    current_kpi, prior_kpi = aggregate_kpis(current), aggregate_kpis(prior)
    cards = [
        ("On-Time Delivery", "otd", True, False), ("Delivery Success", "success", True, False),
        ("Capacity Utilization", "utilization", True, True), ("POD Compliance", "pod", True, False),
        ("Exception Rate", "exception", True, True), ("Packages / Driver", "packages_per_driver", False, False),
    ]
    cols = st.columns(6)
    for col, (label, key, percent, inverse) in zip(cols, cards):
        value = current_kpi[key]
        delta = (value - prior_kpi[key]) * (100 if percent else 1) if not prior.empty else None
        with col:
            kpi_card(label, f"{value:.1%}" if percent else f"{value:,.1f}", delta, "vs previous period", inverse, "pp" if percent else "pkg")

    section_header("Performance Trend", "Daily OTD with a seven-day operating signal and service target.")
    trend = daily_performance(current)
    st.plotly_chart(trend_chart(trend.rename(columns={"otd": "on_time_delivery_rate"}), "on_time_delivery_rate", "rolling_7d_otd"), width="stretch", config={"displayModeBar": False})

    left, right = st.columns([.85, 1.15])
    with left:
        section_header("Station Performance", "Package-weighted OTD ranking for the selected period.")
        stations = grouped_performance(current, ["station_id"])
        st.plotly_chart(horizontal_rank(stations, "station_id", "otd"), width="stretch", config={"displayModeBar": False})
    with right:
        section_header("DSP Leaderboard", "Provider execution, capacity pressure and current operating status.")
        dsps = grouped_performance(current, ["provider_id"])
        dsps["Rank"] = dsps["otd"].rank(method="dense", ascending=False).astype(int)
        dsps["Status"] = dsps.apply(lambda r: operational_status(r.otd, r.exception_rate, r.utilization), axis=1)
        dsps["Trend"] = dsps["otd"] - dsps["otd"].mean()
        display = dsps[["Rank", "provider_id", "otd", "utilization", "pickup_delay", "exception_rate", "Trend", "Status"]].sort_values("Rank")
        st.dataframe(display, hide_index=True, width="stretch", height=290,
            column_config={"provider_id": "DSP", "otd": st.column_config.ProgressColumn("OTD", format="%.1%%", min_value=0, max_value=1),
                "utilization": st.column_config.NumberColumn("Capacity", format="%.1%%"), "pickup_delay": st.column_config.NumberColumn("Pickup Delay", format="%.1f min"),
                "exception_rate": st.column_config.NumberColumn("Exception", format="%.1%%"), "Trend": st.column_config.NumberColumn("vs Network", format="%+.1%%")})

    section_header("Capacity Utilization vs OTD", "Bubble size represents route volume; reference lines highlight emerging capacity pressure.")
    st.plotly_chart(scatter_capacity(current), width="stretch", config={"displayModeBar": False})
