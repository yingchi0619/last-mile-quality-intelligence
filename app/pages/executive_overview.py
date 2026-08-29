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
from app.i18n import local_status, tr
from app.utils import aggregate_kpis, daily_performance, grouped_performance, prior_period


def render(routes: pd.DataFrame) -> None:
    latest = routes["service_date"].max().strftime("%b %d, %Y")
    page_header(tr("Regional Performance Overview", "区域绩效总览"), tr("Monitor delivery quality, capacity health and network performance.", "监控配送质量、运力健康度与区域网络绩效。"), latest)
    filters = filter_bar(routes, "exec", 30)
    current = apply_filters(routes, filters)
    if current.empty:
        st.info(tr("No operating records match the selected filters. Reset filters to restore the network view.", "没有符合当前筛选条件的运营记录，请重置筛选条件。"))
        return
    prior = prior_period(routes, current)
    current_kpi, prior_kpi = aggregate_kpis(current), aggregate_kpis(prior)
    cards = [
        (tr("On-Time Delivery", "准时送达率"), "otd", True, False), (tr("Delivery Success", "配送成功率"), "success", True, False),
        (tr("Capacity Utilization", "运力利用率"), "utilization", True, True), (tr("POD Compliance", "妥投证明合规率"), "pod", True, False),
        (tr("Exception Rate", "异常率"), "exception", True, True), (tr("Packages / Driver", "每名司机包裹数"), "packages_per_driver", False, False),
    ]
    cols = st.columns(6)
    for col, (label, key, percent, inverse) in zip(cols, cards):
        value = current_kpi[key]
        delta = (value - prior_kpi[key]) * (100 if percent else 1) if not prior.empty else None
        with col:
            kpi_card(label, f"{value:.1%}" if percent else f"{value:,.1f}", delta, tr("vs previous period", "较上一周期"), inverse, tr("pp", "百分点") if percent else tr("pkg", "件"))

    section_header(tr("Performance Trend", "绩效趋势"), tr("Daily OTD with a seven-day operating signal and service target.", "每日准时送达率、7日滚动趋势与服务目标。"))
    trend = daily_performance(current)
    st.plotly_chart(trend_chart(trend.rename(columns={"otd": "on_time_delivery_rate"}), "on_time_delivery_rate", "rolling_7d_otd"), use_container_width=True, config={"displayModeBar": False})

    left, right = st.columns([.85, 1.15])
    with left:
        section_header(tr("Station Performance", "站点绩效"), tr("Package-weighted OTD ranking for the selected period.", "所选期间按包裹量加权的准时送达率排名。"))
        stations = grouped_performance(current, ["station_id"])
        st.plotly_chart(horizontal_rank(stations, "station_id", "otd"), use_container_width=True, config={"displayModeBar": False})
    with right:
        section_header(tr("DSP Leaderboard", "DSP 排行榜"), tr("Provider execution, capacity pressure and current operating status.", "服务商执行、运力压力与当前运营状态。"))
        dsps = grouped_performance(current, ["provider_id"])
        dsps["Rank"] = dsps["otd"].rank(method="dense", ascending=False).astype(int)
        dsps["Status"] = dsps.apply(lambda r: operational_status(r.otd, r.exception_rate, r.utilization), axis=1)
        dsps["Status"] = dsps["Status"].map(local_status)
        dsps["Trend"] = dsps["otd"] - dsps["otd"].mean()
        display = dsps[["Rank", "provider_id", "otd", "utilization", "pickup_delay", "exception_rate", "Trend", "Status"]].sort_values("Rank")
        st.dataframe(display, hide_index=True, width="stretch", height=290,
            column_config={"Rank": tr("Rank", "排名"), "provider_id": "DSP", "otd": st.column_config.ProgressColumn(tr("OTD", "准时送达率"), format="%.1%%", min_value=0, max_value=1),
                "utilization": st.column_config.NumberColumn(tr("Capacity", "运力利用率"), format="%.1%%"), "pickup_delay": st.column_config.NumberColumn(tr("Pickup Delay", "提货延迟"), format="%.1f min"),
                "exception_rate": st.column_config.NumberColumn(tr("Exception", "异常率"), format="%.1%%"), "Trend": st.column_config.NumberColumn(tr("vs Network", "较区域网络"), format="%+.1%%"), "Status": tr("Status", "状态")})

    section_header(tr("Capacity Utilization vs OTD", "运力利用率与准时送达率"), tr("Bubble size represents route volume; reference lines highlight emerging capacity pressure.", "气泡大小代表路线包裹量，参考线用于识别运力压力。"))
    st.plotly_chart(scatter_capacity(current), use_container_width=True, config={"displayModeBar": False})
