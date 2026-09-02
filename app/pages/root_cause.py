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
from app.i18n import tr
from app.utils import grouped_performance


def _band_summary(data: pd.DataFrame, factor: str, bins: list[float], labels: list[str]) -> pd.DataFrame:
    working = data.assign(Band=pd.cut(data[factor], bins=bins, labels=labels, include_lowest=True))
    return grouped_performance(working, ["Band"])


def _bar_line(summary: pd.DataFrame, label: str = "Band") -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=summary[label].astype(str), y=summary["otd"], marker_color=BLUE, name=tr("OTD", "准时送达率"), text=[f"{v:.1%}" for v in summary.otd], textposition="outside"))
    fig.add_trace(go.Scatter(x=summary[label].astype(str), y=summary["exception_rate"], mode="lines+markers", line=dict(color=ORANGE, width=2), name=tr("Exception", "异常率")))
    fig.update_yaxes(tickformat=".0%", range=[0, 1])
    return style_figure(fig, 310, True)


def render(routes: pd.DataFrame) -> None:
    page_header(tr("Root Cause Analysis", "根因分析"), tr("Understand what is driving service quality changes.", "识别服务质量变化背后的运营驱动因素。"), routes["service_date"].max().strftime("%b %d, %Y"))
    current = apply_filters(routes, filter_bar(routes, "rca", 90))
    if current.empty:
        st.info(tr("No diagnostic records match the selected operating slice.", "没有符合当前运营筛选范围的诊断记录。"))
        return
    thresholds = processed_csv("threshold_analysis.csv")
    trends = processed_csv("week_over_week_trends.csv")
    pareto = processed_csv("exception_pareto_analysis.csv")
    anomalies = processed_csv("zscore_anomalies.csv")

    section_header(tr("Key Diagnostic Findings", "关键诊断发现"), tr("Automatically calculated from synthetic historical relationships.", "根据虚构历史数据关系自动计算。"))
    capacity = thresholds[thresholds.factor == "capacity_utilization"].iloc[0]
    pickup = thresholds[thresholds.factor == "pickup_delay_minutes"].iloc[0]
    density = thresholds[thresholds.factor == "route_density"].iloc[0]
    worst_dsp = trends[trends.entity_type == "DSP"].sort_values("otd_change_percentage_points").iloc[0]
    cols = st.columns(4)
    with cols[0]: insight_card(tr("Capacity Pressure", "运力压力"), tr(f"> {capacity.threshold:.0%} utilization", f"> {capacity.threshold:.0%} 利用率"), tr(f"OTD is {capacity.otd_impact_percentage_points:.1f} pp lower than the comparison group.", f"准时送达率较对照组低 {capacity.otd_impact_percentage_points:.1f} 个百分点。"), "red")
    with cols[1]: insight_card(tr("Pickup Execution", "提货执行"), tr(f"> {pickup.threshold:.1f} minutes", f"> {pickup.threshold:.1f} 分钟"), tr(f"OTD is {pickup.otd_impact_percentage_points:.1f} pp lower after the observed breakpoint.", f"超过该观察阈值后，准时送达率低 {pickup.otd_impact_percentage_points:.1f} 个百分点。"), "orange")
    with cols[2]: insight_card(tr("Route Density", "路线密度"), tr(f"< {density.threshold:.2f} density", f"< {density.threshold:.2f} 密度"), tr(f"Low-density exposure is associated with a {density.otd_impact_percentage_points:.1f} pp OTD gap.", f"低密度路线与 {density.otd_impact_percentage_points:.1f} 个百分点的准时送达率差距相关。"), "blue")
    with cols[3]: insight_card(tr("Recent DSP Trend", "近期 DSP 趋势"), str(worst_dsp.entity_id), tr(f"Latest 7-day OTD changed {worst_dsp.otd_change_percentage_points:+.1f} pp versus the prior 30 days.", f"最近7日准时送达率较此前30日变化 {worst_dsp.otd_change_percentage_points:+.1f} 个百分点。"), "orange")

    section_header(tr("Operational Factor Diagnostics", "运营因素诊断"), tr("OTD bars with exception-rate overlays reveal nonlinear breakpoints.", "准时送达率柱状图叠加异常率趋势，用于识别非线性拐点。"))
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**{tr('OTD by Capacity Utilization', '按运力利用率分析准时送达率')}**")
        s = _band_summary(current, "capacity_utilization", [-float("inf"), .8, .9, 1, 1.1, float("inf")], ["<80%", "80–90%", "90–100%", "100–110%", "110%+"])
        st.plotly_chart(_bar_line(s), use_container_width=True, config={"displayModeBar":False})
    with c2:
        st.markdown(f"**{tr('OTD by Pickup Delay', '按提货延迟分析准时送达率')}**")
        s = _band_summary(current, "pickup_delay_minutes", [-float("inf"), 5, 10, 20, 30, float("inf")], ["0–5", "5–10", "10–20", "20–30", "30+"])
        st.plotly_chart(_bar_line(s), use_container_width=True, config={"displayModeBar":False})
    with c3:
        st.markdown(f"**{tr('OTD by Route Density', '按路线密度分析准时送达率')}**")
        q1, q2 = current.route_density.quantile([.33, .67])
        s = _band_summary(current, "route_density", [-float("inf"), q1, q2, float("inf")], [tr("Low", "低"), tr("Medium", "中"), tr("High", "高")])
        st.plotly_chart(_bar_line(s), use_container_width=True, config={"displayModeBar":False})

    left, right = st.columns([1.15, .85])
    with left:
        section_header(tr("Main Problem Types", "主要问题类型"), tr("Most common issue categories and their cumulative share.", "最常见的问题类型及其累计占比。"))
        p = pareto.copy()
        exception_labels = {"LATE_DELIVERY":"延迟送达", "RECIPIENT_UNAVAILABLE":"收件人无法接收", "ACCESS_ISSUE":"进入受阻", "RETURN_TO_ORIGIN":"退回始发站", "PROCESS_EXCEPTION":"流程异常", "STATION_SORT_DELAY":"站点分拣延迟", "PROVIDER_CAPACITY_STRESS":"服务商运力压力", "LOCAL_PROCESS_DISRUPTION":"本地流程中断"}
        p["exception_label"] = p.exception_type.map(exception_labels) if st.session_state.get("language_zh") else p.exception_type
        fig = go.Figure()
        fig.add_trace(go.Bar(x=p.exception_label, y=p.exception_packages, marker_color=BLUE, name=tr("Exceptions", "异常包裹")))
        fig.add_trace(go.Scatter(x=p.exception_label, y=p.cumulative_exception_share, yaxis="y2", line=dict(color=ORANGE, width=3), mode="lines+markers", name=tr("Cumulative", "累计占比")))
        fig.add_trace(go.Scatter(x=p.exception_label, y=[.8] * len(p), yaxis="y2", mode="lines", line=dict(color=RED, dash="dot"), name=tr("80% reference", "80%参考线")))
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", tickformat=".0%", range=[0,1.08], showgrid=False))
        st.plotly_chart(style_figure(fig, 370, True), use_container_width=True, config={"displayModeBar":False})
    with right:
        section_header(tr("Operational Anomalies", "运营异常"), tr("Rolling z-score alerts generated from observed performance.", "根据观察绩效生成的滚动 z-score 预警。"))
        with st.container(border=True):
            if anomalies.empty:
                st.success(tr("No material anomalies were detected for this period.", "当前期间未发现重大异常。"))
            else:
                for row in anomalies.head(5).itertuples():
                    severity = tr("HIGH", "高") if row.anomaly_severity >= 3 else tr("MEDIUM", "中")
                    css = "red" if row.anomaly_severity >= 3 else "orange"
                    anomaly_label = row.anomaly_type.replace("_", " ") if not st.session_state.get("language_zh") else row.anomaly_type.replace("OTD_DROP", "准时送达率下降").replace("EXCEPTION_SPIKE", "异常率上升").replace("_", " ")
                    st.markdown(f'<div class="alert-row"><span class="badge badge-{css}">{severity}</span><div class="alert-content"><strong>{row.entity_id} · {anomaly_label}</strong><p>{str(row.service_date)[:10]} · z-score {row.anomaly_severity:.1f}</p></div></div>', unsafe_allow_html=True)
