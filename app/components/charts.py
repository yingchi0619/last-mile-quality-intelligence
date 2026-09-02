"""Consistent Plotly styling and chart builders."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.i18n import tr

BLUE = "#2563EB"
BLUE_LIGHT = "#93C5FD"
GREEN = "#16A34A"
ORANGE = "#D97706"
RED = "#DC2626"
SLATE = "#64748B"
PALETTE = ["#2563EB", "#5B7FA3", "#2F855A", "#B7791F", "#7C6F9F"]


def style_figure(fig: go.Figure, height: int = 360, legend: bool = False) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=12, r=16, t=12, b=12),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, ui-sans-serif, system-ui", color="#334155", size=12),
        showlegend=legend, hoverlabel=dict(bgcolor="#0F172A", font_color="white", bordercolor="#0F172A"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(showgrid=False, linecolor="#E2E8F0", tickfont_color="#64748B", title_font_color="#64748B")
    fig.update_yaxes(gridcolor="#EDF2F7", zeroline=False, tickfont_color="#64748B", title_font_color="#64748B")
    return fig


def trend_chart(data: pd.DataFrame, value: str, rolling: str, target: float = 0.95) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data["service_date"], y=data[value], mode="lines", line=dict(color=BLUE_LIGHT, width=1.5), fill="tozeroy", fillcolor="rgba(37,99,235,.06)", name=tr("Daily", "每日")))
    fig.add_trace(go.Scatter(x=data["service_date"], y=data[rolling], mode="lines", line=dict(color=BLUE, width=3), name=tr("7-day rolling", "7日滚动平均")))
    fig.add_hline(y=target, line_dash="dot", line_color=ORANGE, annotation_text=f"{tr('Target', '目标')} {target:.0%}", annotation_position="top left")
    fig.update_yaxes(tickformat=".0%", range=[max(0, data[value].min() - .08), 1])
    return style_figure(fig, 380, True)


def scatter_capacity(data: pd.DataFrame) -> go.Figure:
    fig = px.scatter(data, x="capacity_utilization", y="on_time_delivery_rate", size="actual_packages", color="provider_id", color_discrete_sequence=PALETTE, hover_data=["route_line_id", "station_id", "pickup_delay_minutes"], opacity=.72)
    fig.add_vline(x=.90, line_dash="dot", line_color="#94A3B8", annotation_text="90%")
    fig.add_vline(x=1.0, line_dash="dash", line_color=ORANGE, annotation_text="100%")
    fig.update_xaxes(tickformat=".0%")
    fig.update_yaxes(tickformat=".0%")
    fig.update_xaxes(title=tr("Capacity Utilization", "运力利用率"))
    fig.update_yaxes(title=tr("On-Time Delivery", "准时送达率"))
    return style_figure(fig, 410, True)


def horizontal_rank(data: pd.DataFrame, label: str, value: str) -> go.Figure:
    ordered = data.sort_values(value)
    colors = [RED if v < .82 else ORANGE if v < .90 else BLUE for v in ordered[value]]
    fig = go.Figure(go.Bar(x=ordered[value], y=ordered[label], orientation="h", marker_color=colors, text=[f"{v:.1%}" for v in ordered[value]], textposition="outside"))
    fig.update_xaxes(tickformat=".0%", range=[max(0, ordered[value].min() - .08), 1])
    return style_figure(fig, 290)
