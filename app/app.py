"""Last-Mile Operations Intelligence Streamlit application."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app.components.theme import inject_theme
from app.data import route_data
from app.i18n import tr
from app.pages import capacity_planning, executive_overview, root_cause, route_risk, station_dsp

st.set_page_config(
    page_title="Last-Mile Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_theme()

with st.sidebar:
    st.markdown('<div class="sidebar-brand"><span class="brand-mark">LM</span><span class="brand-title">Last-Mile Intelligence</span></div>', unsafe_allow_html=True)
    nav_labels = {
        "executive": tr("01  Executive Overview", "01  管理层总览"),
        "station_dsp": tr("02  Station & DSP Performance", "02  站点与 DSP 绩效"),
        "root_cause": tr("03  Root Cause Analysis", "03  根因分析"),
        "capacity": tr("04  Capacity Planning", "04  运力规划"),
        "route_risk": tr("05  Route Risk", "05  路线风险"),
    }
    page = st.radio(
        tr("Platform Navigation", "平台导航"),
        list(nav_labels),
        format_func=nav_labels.get,
        key="nav_page",
        label_visibility="collapsed",
    )
    with st.expander(tr("About this platform", "关于本平台")):
        st.markdown(
            tr(
                "**Synthetic Data**\n\nThis dashboard uses entirely synthetic data created for portfolio demonstration purposes.\n\nNo proprietary, confidential, customer, driver, route, pricing, or operational data from any current or former employer is included.",
                "**虚构数据**\n\n本仪表板仅使用为作品集演示而创建的完全虚构数据。\n\n不包含任何现任或前任雇主的专有、保密、客户、司机、路线、价格或运营数据。",
            )
        )
    st.markdown(f'<div class="sidebar-footer"><strong>{tr("PORTFOLIO DEMONSTRATION", "作品集演示项目")}</strong><br>{tr("Synthetic Operational Data", "虚构运营数据")}<br><br>{tr("Quality · Capacity · Risk", "质量 · 运力 · 风险")}</div>', unsafe_allow_html=True)

st.markdown(
    f'<div class="platform-strip"><div><span class="platform-eyebrow">{tr("OPERATIONS CONTROL TOWER", "运营控制塔")}</span><strong>{tr("Last-Mile Operations Intelligence", "最后一公里运营智能")}</strong><small>{tr("Regional Quality, Capacity & Delivery Performance", "区域质量、运力与配送绩效")}</small></div></div>',
    unsafe_allow_html=True,
)

routes = route_data()
pages = {
    "executive": executive_overview.render,
    "station_dsp": station_dsp.render,
    "root_cause": root_cause.render,
    "capacity": capacity_planning.render,
    "route_risk": route_risk.render,
}

try:
    pages[page](routes)
except Exception as exc:
    st.error(tr("This view could not be rendered. Reset the page filters and try again.", "此页面暂时无法加载，请重置筛选条件后重试。"))
    with st.expander(tr("Technical detail", "技术详情")):
        st.exception(exc)
