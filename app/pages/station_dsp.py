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
from app.i18n import local_status, tr
from app.utils import aggregate_kpis, daily_performance, grouped_performance, prior_period


def render(routes: pd.DataFrame) -> None:
    page_header(tr("Station & DSP Performance", "站点与 DSP 绩效"), tr("Drill into provider performance, route execution and operational trends.", "深入分析服务商绩效、路线执行与运营趋势。"), routes["service_date"].max().strftime("%b %d, %Y"))
    current = apply_filters(routes, filter_bar(routes, "ops", 30))
    if current.empty:
        st.info(tr("No station or DSP records match this filter combination.", "没有符合当前筛选组合的站点或 DSP 记录。"))
        return
    prior = prior_period(routes, current)
    kpis, old = aggregate_kpis(current), aggregate_kpis(prior)
    section_header(tr("Selected Network Summary", "当前网络摘要"), tr("Performance for the active date, station and DSP selection.", "当前日期、站点和 DSP 筛选范围内的绩效。"))
    cols = st.columns(5)
    for col, label, key, percent, inverse in zip(cols,
        [tr("OTD", "准时送达率"), tr("Packages / Driver", "每名司机包裹数"), tr("Capacity Utilization", "运力利用率"), tr("Pickup Delay", "提货延迟"), tr("Exception Rate", "异常率")],
        ["otd", "packages_per_driver", "utilization", "pickup_delay", "exception"],
        [True, False, True, False, True], [False, False, True, True, True]):
        value = kpis[key]
        delta = (value - old[key]) * (100 if percent else 1) if not prior.empty else None
        with col: kpi_card(label, f"{value:.1%}" if percent else f"{value:.1f}", delta, tr("vs prior period", "较上一周期"), inverse, tr("pp", "百分点") if percent else (tr("min", "分钟") if key == "pickup_delay" else tr("pkg", "件")))

    section_header(tr("DSP Ranking", "DSP 排名"), tr("Operational leaderboard using package-weighted quality metrics.", "使用包裹量加权质量指标的运营排行榜。"))
    dsp = grouped_performance(current, ["provider_id"])
    dsp["Rank"] = dsp["otd"].rank(method="dense", ascending=False).astype(int)
    dsp["7-Day Trend"] = dsp["otd"] - dsp["otd"].mean()
    dsp["Status"] = dsp.apply(lambda r: operational_status(r.otd, r.exception_rate, r.utilization), axis=1)
    dsp["Status"] = dsp["Status"].map(local_status)
    st.dataframe(dsp[["Rank", "provider_id", "volume", "otd", "success", "utilization", "packages_per_driver", "pickup_delay", "exception_rate", "7-Day Trend", "Status"]].sort_values("Rank"),
        hide_index=True, width="stretch", height=270,
        column_config={"Rank":tr("Rank", "排名"), "provider_id":"DSP", "volume":st.column_config.NumberColumn(tr("Volume", "包裹量"), format="%,d"),
            "otd":st.column_config.NumberColumn(tr("OTD", "准时送达率"), format="%.1%%"), "success":st.column_config.NumberColumn(tr("Delivery Success", "配送成功率"), format="%.1%%"),
            "utilization":st.column_config.NumberColumn(tr("Capacity", "运力利用率"), format="%.1%%"), "packages_per_driver":st.column_config.NumberColumn(tr("Packages / Driver", "每名司机包裹数"), format="%.1f"),
            "pickup_delay":st.column_config.NumberColumn(tr("Pickup Delay", "提货延迟"), format="%.1f min"), "exception_rate":st.column_config.NumberColumn(tr("Exception", "异常率"), format="%.1%%"),
            "7-Day Trend":st.column_config.NumberColumn(tr("Trend", "7日趋势"), format="%+.1%%"), "Status":tr("Status", "状态")})

    section_header(tr("Operational Trend", "运营趋势"), tr("Compare short- and medium-term operating signals.", "比较短期与中期运营信号。"))
    metric_options = {"OTD": tr("OTD", "准时送达率"), "Exception Rate": tr("Exception Rate", "异常率"), "Capacity Utilization": tr("Capacity Utilization", "运力利用率"), "Packages per Driver": tr("Packages per Driver", "每名司机包裹数")}
    metric = st.selectbox(tr("Metric", "指标"), list(metric_options), format_func=metric_options.get, index=0, key="ops_metric")
    daily = daily_performance(current)
    mapping = {"OTD":("otd", ".0%"), "Exception Rate":("exception_rate", ".0%"), "Capacity Utilization":("utilization", ".0%"), "Packages per Driver":("packages_per_driver", ".0f")}
    value, fmt = mapping[metric]
    rolling7 = daily[value].rolling(7, min_periods=1).mean()
    rolling30 = daily[value].rolling(30, min_periods=1).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily.service_date, y=rolling30, name=tr("30-day", "30日"), line=dict(color="#A8B6C7", width=2)))
    fig.add_trace(go.Scatter(x=daily.service_date, y=rolling7, name=tr("7-day", "7日"), line=dict(color=BLUE, width=3)))
    fig.update_yaxes(tickformat=fmt)
    st.plotly_chart(style_figure(fig, 340, True), use_container_width=True, config={"displayModeBar":False})

    section_header(tr("Route Line Performance", "线路绩效"), tr("Sortable route-line execution detail with subtle risk highlighting.", "可排序的线路执行明细，并以轻量方式突出风险。"))
    table = current.copy()
    table["Risk"] = table.apply(lambda r: operational_status(r.on_time_delivery_rate, r.exception_rate, r.capacity_utilization), axis=1)
    table["Risk"] = table["Risk"].map(local_status)
    table = table[["route_line_id", "route_id", "provider_id", "station_id", "driver_id", "actual_packages", "planned_pickup_timestamp", "actual_pickup_timestamp", "route_density", "capacity_utilization", "pickup_delay_minutes", "on_time_delivery_rate", "exception_packages", "Risk"]]
    st.dataframe(table, hide_index=True, width="stretch", height=440,
        column_config={"route_line_id":tr("Route Line", "线路"), "route_id":tr("Assignment", "任务"), "provider_id":"DSP", "station_id":tr("Station", "站点"), "driver_id":tr("Driver", "司机"), "actual_packages":tr("Volume", "包裹量"),
            "planned_pickup_timestamp":st.column_config.DatetimeColumn(tr("Planned Pickup", "计划提货"), format="HH:mm"), "actual_pickup_timestamp":st.column_config.DatetimeColumn(tr("Actual Pickup", "实际提货"), format="HH:mm"),
            "route_density":st.column_config.NumberColumn(tr("Density", "路线密度"), format="%.2f"), "capacity_utilization":st.column_config.ProgressColumn(tr("Utilization", "利用率"), min_value=0, max_value=1.3, format="%.1%%"),
            "pickup_delay_minutes":st.column_config.NumberColumn(tr("Pickup Delay", "提货延迟"), format="%.1f min"), "on_time_delivery_rate":st.column_config.ProgressColumn(tr("OTD", "准时送达率"), min_value=0, max_value=1, format="%.1%%"), "exception_packages":tr("Exceptions", "异常包裹"), "Risk":tr("Risk", "风险")})
