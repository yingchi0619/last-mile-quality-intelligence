"""Operational root-cause analysis page."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.components.charts import BLUE, ORANGE, RED, style_figure
from app.components.filter_bar import apply_filters, filter_bar
from app.components.insight_card import insight_card
from app.components.theme import page_header, section_header
from app.data import processed_csv
from app.utils import grouped_performance


def _band_summary(data: pd.DataFrame, factor: str, bins: list[float], labels: list[str]) -> pd.DataFrame:
    working = data.assign(Band=pd.cut(data[factor], bins=bins, labels=labels, include_lowest=True))
    return grouped_performance(working, ["Band"])


def _bar_line(summary: pd.DataFrame, label: str = "Band") -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=summary[label].astype(str), y=summary["otd"], marker_color=BLUE, name="OTD", text=[f"{v:.1%}" for v in summary.otd], textposition="outside"))
    fig.add_trace(go.Scatter(x=summary[label].astype(str), y=summary["exception_rate"], mode="lines+markers", line=dict(color=ORANGE, width=2), name="Exception"))
    fig.update_yaxes(tickformat=".0%", range=[0, 1])
    return style_figure(fig, 310, True)


def render(routes: pd.DataFrame) -> None:
    page_header("Root Cause Analysis", "Understand what is driving service quality changes.", routes["service_date"].max().strftime("%b %d, %Y"))
    current = apply_filters(routes, filter_bar(routes, "rca", 90))
    if current.empty:
        st.info("No diagnostic records match the selected operating slice.")
        return
    thresholds = processed_csv("threshold_analysis.csv")
    trends = processed_csv("week_over_week_trends.csv")
    pareto = processed_csv("exception_pareto_analysis.csv")
    anomalies = processed_csv("zscore_anomalies.csv")

    section_header("Key Diagnostic Findings", "Automatically calculated from synthetic historical relationships.")
    capacity = thresholds[thresholds.factor == "capacity_utilization"].iloc[0]
    pickup = thresholds[thresholds.factor == "pickup_delay_minutes"].iloc[0]
    density = thresholds[thresholds.factor == "route_density"].iloc[0]
    worst_dsp = trends[trends.entity_type == "DSP"].sort_values("otd_change_percentage_points").iloc[0]
    cols = st.columns(4)
    with cols[0]: insight_card("Capacity Pressure", f"> {capacity.threshold:.0%} utilization", f"OTD is {capacity.otd_impact_percentage_points:.1f} pp lower than the comparison group.", "red")
    with cols[1]: insight_card("Pickup Execution", f"> {pickup.threshold:.1f} minutes", f"OTD is {pickup.otd_impact_percentage_points:.1f} pp lower after the observed breakpoint.", "orange")
    with cols[2]: insight_card("Route Density", f"< {density.threshold:.2f} density", f"Low-density exposure is associated with a {density.otd_impact_percentage_points:.1f} pp OTD gap.", "blue")
    with cols[3]: insight_card("Recent DSP Trend", str(worst_dsp.entity_id), f"Latest 7-day OTD changed {worst_dsp.otd_change_percentage_points:+.1f} pp versus the prior 30 days.", "orange")

    section_header("Operational Factor Diagnostics", "OTD bars with exception-rate overlays reveal nonlinear breakpoints.")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**OTD by Capacity Utilization**")
        s = _band_summary(current, "capacity_utilization", [-float("inf"), .8, .9, 1, 1.1, float("inf")], ["<80%", "80–90%", "90–100%", "100–110%", "110%+"])
        st.plotly_chart(_bar_line(s), width="stretch", config={"displayModeBar":False})
    with c2:
        st.markdown("**OTD by Pickup Delay**")
        s = _band_summary(current, "pickup_delay_minutes", [-float("inf"), 5, 10, 20, 30, float("inf")], ["0–5", "5–10", "10–20", "20–30", "30+"])
        st.plotly_chart(_bar_line(s), width="stretch", config={"displayModeBar":False})
    with c3:
        st.markdown("**OTD by Route Density**")
        q1, q2 = current.route_density.quantile([.33, .67])
        s = _band_summary(current, "route_density", [-float("inf"), q1, q2, float("inf")], ["Low", "Medium", "High"])
        st.plotly_chart(_bar_line(s), width="stretch", config={"displayModeBar":False})

    left, right = st.columns([1.15, .85])
    with left:
        section_header("Exception Pareto Analysis", "Leading exception categories and cumulative contribution.")
        p = pareto.copy()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=p.exception_type, y=p.exception_packages, marker_color=BLUE, name="Exceptions"))
        fig.add_trace(go.Scatter(x=p.exception_type, y=p.cumulative_exception_share, yaxis="y2", line=dict(color=ORANGE, width=3), mode="lines+markers", name="Cumulative"))
        fig.add_trace(go.Scatter(x=p.exception_type, y=[.8] * len(p), yaxis="y2", mode="lines", line=dict(color=RED, dash="dot"), name="80% reference"))
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", tickformat=".0%", range=[0,1.08], showgrid=False))
        st.plotly_chart(style_figure(fig, 370, True), width="stretch", config={"displayModeBar":False})
    with right:
        section_header("Operational Anomalies", "Rolling z-score alerts generated from observed performance.")
        with st.container(border=True):
            if anomalies.empty:
                st.success("No material anomalies were detected for this period.")
            else:
                for row in anomalies.head(5).itertuples():
                    severity = "HIGH" if row.anomaly_severity >= 3 else "MEDIUM"
                    css = "red" if severity == "HIGH" else "orange"
                    st.markdown(f'<div class="alert-row"><span class="badge badge-{css}">{severity}</span><div class="alert-content"><strong>{row.entity_id} · {row.anomaly_type.replace("_", " ")}</strong><p>{str(row.service_date)[:10]} · z-score {row.anomaly_severity:.1f}</p></div></div>', unsafe_allow_html=True)
