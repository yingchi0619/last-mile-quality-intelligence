"""Station and DSP drill-down page."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.components.charts import BLUE, ORANGE, style_figure
from app.components.filter_bar import apply_filters, filter_bar
from app.components.kpi_card import kpi_card
from app.components.status_badge import operational_status
from app.components.theme import page_header, section_header
from app.utils import aggregate_kpis, daily_performance, grouped_performance, prior_period


def render(routes: pd.DataFrame) -> None:
    page_header("Station & DSP Performance", "Drill into provider performance, route execution and operational trends.", routes["service_date"].max().strftime("%b %d, %Y"))
    current = apply_filters(routes, filter_bar(routes, "ops", 30))
    if current.empty:
        st.info("No station or DSP records match this filter combination.")
        return
    prior = prior_period(routes, current)
    kpis, old = aggregate_kpis(current), aggregate_kpis(prior)
    section_header("Selected Network Summary", "Performance for the active date, station and DSP selection.")
    cols = st.columns(5)
    for col, label, key, percent, inverse in zip(cols,
        ["OTD", "Packages / Driver", "Capacity Utilization", "Pickup Delay", "Exception Rate"],
        ["otd", "packages_per_driver", "utilization", "pickup_delay", "exception"],
        [True, False, True, False, True], [False, False, True, True, True]):
        value = kpis[key]
        delta = (value - old[key]) * (100 if percent else 1) if not prior.empty else None
        with col: kpi_card(label, f"{value:.1%}" if percent else f"{value:.1f}", delta, "vs prior period", inverse, "pp" if percent else ("min" if key == "pickup_delay" else "pkg"))

    section_header("DSP Ranking", "Operational leaderboard using package-weighted quality metrics.")
    dsp = grouped_performance(current, ["provider_id"])
    dsp["Rank"] = dsp["otd"].rank(method="dense", ascending=False).astype(int)
    dsp["7-Day Trend"] = dsp["otd"] - dsp["otd"].mean()
    dsp["Status"] = dsp.apply(lambda r: operational_status(r.otd, r.exception_rate, r.utilization), axis=1)
    st.dataframe(dsp[["Rank", "provider_id", "volume", "otd", "success", "utilization", "packages_per_driver", "pickup_delay", "exception_rate", "7-Day Trend", "Status"]].sort_values("Rank"),
        hide_index=True, width="stretch", height=270,
        column_config={"provider_id":"DSP", "volume":st.column_config.NumberColumn("Volume", format="%,d"),
            "otd":st.column_config.NumberColumn("OTD", format="%.1%%"), "success":st.column_config.NumberColumn("Delivery Success", format="%.1%%"),
            "utilization":st.column_config.NumberColumn("Capacity", format="%.1%%"), "packages_per_driver":st.column_config.NumberColumn("Packages / Driver", format="%.1f"),
            "pickup_delay":st.column_config.NumberColumn("Pickup Delay", format="%.1f min"), "exception_rate":st.column_config.NumberColumn("Exception", format="%.1%%"),
            "7-Day Trend":st.column_config.NumberColumn("Trend", format="%+.1%%")})

    section_header("Operational Trend", "Compare short- and medium-term operating signals.")
    metric = st.selectbox("Metric", ["OTD", "Exception Rate", "Capacity Utilization", "Packages per Driver"], index=0, key="ops_metric")
    daily = daily_performance(current)
    mapping = {"OTD":("otd", ".0%"), "Exception Rate":("exception_rate", ".0%"), "Capacity Utilization":("utilization", ".0%"), "Packages per Driver":("packages_per_driver", ".0f")}
    value, fmt = mapping[metric]
    rolling7 = daily[value].rolling(7, min_periods=1).mean()
    rolling30 = daily[value].rolling(30, min_periods=1).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily.service_date, y=rolling30, name="30-day", line=dict(color="#A8B6C7", width=2)))
    fig.add_trace(go.Scatter(x=daily.service_date, y=rolling7, name="7-day", line=dict(color=BLUE, width=3)))
    fig.update_yaxes(tickformat=fmt)
    st.plotly_chart(style_figure(fig, 340, True), width="stretch", config={"displayModeBar":False})

    section_header("Route Performance", "Sortable route execution detail with subtle risk highlighting.")
    table = current.copy()
    table["Risk"] = table.apply(lambda r: operational_status(r.on_time_delivery_rate, r.exception_rate, r.capacity_utilization), axis=1)
    table = table[["route_id", "provider_id", "station_id", "actual_packages", "route_density", "capacity_utilization", "pickup_delay_minutes", "on_time_delivery_rate", "exception_packages", "Risk"]]
    st.dataframe(table, hide_index=True, width="stretch", height=440,
        column_config={"route_id":"Route", "provider_id":"DSP", "station_id":"Station", "actual_packages":"Volume",
            "route_density":st.column_config.NumberColumn("Density", format="%.2f"), "capacity_utilization":st.column_config.ProgressColumn("Utilization", min_value=0, max_value=1.3, format="%.1%%"),
            "pickup_delay_minutes":st.column_config.NumberColumn("Pickup Delay", format="%.1f min"), "on_time_delivery_rate":st.column_config.ProgressColumn("OTD", min_value=0, max_value=1, format="%.1%%"), "exception_packages":"Exceptions"})
