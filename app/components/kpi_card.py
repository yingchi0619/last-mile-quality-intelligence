"""Reusable KPI card."""

import math
from typing import Optional
import streamlit as st


def kpi_card(name: str, value: str, delta: Optional[float], context: str, inverse: bool = False, delta_suffix: str = "pp") -> None:
    if delta is None or (isinstance(delta, float) and math.isnan(delta)):
        delta_html = '<span class="delta neutral">— No comparison</span>'
    else:
        good = delta < 0 if inverse else delta > 0
        css = "positive" if good else ("negative" if delta != 0 else "neutral")
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
        delta_html = f'<span class="delta {css}">{arrow} {abs(delta):.1f} {delta_suffix}</span>'
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-label">{name}</div><div class="kpi-value">{value}</div><div class="kpi-footer">{delta_html}<span>{context}</span></div></div>',
        unsafe_allow_html=True,
    )
