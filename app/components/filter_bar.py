"""Unified horizontal dashboard filter bar."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def filter_bar(data: pd.DataFrame, key_prefix: str, default_days: int = 30) -> tuple[pd.Timestamp, pd.Timestamp, list[str], list[str]]:
    minimum, maximum = data["service_date"].min().date(), data["service_date"].max().date()
    default_start = max(minimum, (pd.Timestamp(maximum) - pd.Timedelta(days=default_days - 1)).date())
    stations = sorted(data["station_id"].unique())
    providers = sorted(data["provider_id"].unique())
    with st.container(border=True):
        st.markdown('<div class="filter-label">GLOBAL FILTERS</div>', unsafe_allow_html=True)
        date_col, station_col, dsp_col, reset_col = st.columns([1.45, 1, 1, 0.45], vertical_alignment="bottom")
        with date_col:
            selected_dates = st.date_input(
                "Date range", value=(default_start, maximum), min_value=minimum, max_value=maximum,
                key=f"{key_prefix}_dates",
            )
        with station_col:
            selected_stations = st.multiselect("Station", stations, default=stations, key=f"{key_prefix}_stations")
        with dsp_col:
            selected_dsps = st.multiselect("DSP", providers, default=providers, key=f"{key_prefix}_dsps")
        with reset_col:
            if st.button("Reset", key=f"{key_prefix}_reset", width="stretch"):
                for suffix in ["dates", "stations", "dsps"]:
                    st.session_state.pop(f"{key_prefix}_{suffix}", None)
                st.rerun()
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start, end = selected_dates
    else:
        start = end = selected_dates[0] if isinstance(selected_dates, tuple) else selected_dates
    return pd.Timestamp(start), pd.Timestamp(end), selected_stations, selected_dsps


def apply_filters(data: pd.DataFrame, filters: tuple[pd.Timestamp, pd.Timestamp, list[str], list[str]]) -> pd.DataFrame:
    start, end, stations, dsps = filters
    return data[
        data["service_date"].between(start, end)
        & data["station_id"].isin(stations)
        & data["provider_id"].isin(dsps)
    ].copy()
