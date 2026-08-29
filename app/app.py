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
    page = st.radio(
        "Platform Navigation",
        [
            "01  Executive Overview",
            "02  Station & DSP Performance",
            "03  Root Cause Analysis",
            "04  Capacity Planning",
            "05  Route Risk",
        ],
        label_visibility="collapsed",
    )
    with st.expander("About this platform"):
        st.markdown(
            "**Synthetic Data**\n\nThis dashboard uses entirely synthetic data created for portfolio demonstration purposes.\n\n"
            "No proprietary, confidential, customer, driver, route, pricing, or operational data from any current or former employer is included."
        )
    st.markdown('<div class="sidebar-footer"><strong>PORTFOLIO DEMONSTRATION</strong><br>Synthetic Operational Data<br><br>Quality · Capacity · Risk</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="platform-strip"><div><span class="platform-eyebrow">OPERATIONS CONTROL TOWER</span><strong>Last-Mile Operations Intelligence</strong><small>Regional Quality, Capacity & Delivery Performance</small></div></div>',
    unsafe_allow_html=True,
)

routes = route_data()
pages = {
    "01  Executive Overview": executive_overview.render,
    "02  Station & DSP Performance": station_dsp.render,
    "03  Root Cause Analysis": root_cause.render,
    "04  Capacity Planning": capacity_planning.render,
    "05  Route Risk": route_risk.render,
}

try:
    pages[page](routes)
except Exception as exc:
    st.error("This view could not be rendered. Reset the page filters and try again.")
    with st.expander("Technical detail"):
        st.exception(exc)
