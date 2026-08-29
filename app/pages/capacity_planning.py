"""Interactive capacity-planning simulation page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components.kpi_card import kpi_card
from app.components.theme import page_header, section_header
from app.data import capacity_simulator


def _state_panel(title: str, provider: str, before: pd.Series, after: pd.Series) -> None:
    st.markdown(f"### {title} · `{provider}`")
    cols = st.columns(4)
    metrics = [
        ("Utilization", "utilization", True, True), ("Expected OTD", "expected_otd", True, False),
        ("Packages / Driver", "packages_per_driver", False, True), ("Exception Risk", "exception_risk", True, True),
    ]
    for col, (label, key, percent, inverse) in zip(cols, metrics):
        delta = (after[key] - before[key]) * (100 if percent else 1)
        with col: kpi_card(label, f"{after[key]:.1%}" if percent else f"{after[key]:.1f}", delta, "after vs before", inverse, "pp" if percent else "pkg")
    st.progress(min(float(after["utilization"]), 1.0), text=f"Capacity load: {before['utilization']:.1%} → {after['utilization']:.1%}")


def render(routes: pd.DataFrame) -> None:
    page_header("Capacity Planning Simulator", "Evaluate package reallocation scenarios before operational execution.", routes["service_date"].max().strftime("%b %d, %Y"))
    simulator = capacity_simulator()
    default = simulator.select_sample_scenario(.95)
    states = simulator.daily_states
    left, right = st.columns([.34, .66], gap="large")
    with left:
        section_header("Scenario Controls", "Configure a same-day, same-station volume transfer.")
        with st.container(border=True):
            date_options = sorted(states.service_date.dt.date.unique(), reverse=True)
            default_date = pd.Timestamp(default.overloaded.service_date).date()
            scenario_date = st.selectbox("Scenario date", date_options, index=date_options.index(default_date))
            day_states = states[states.service_date.dt.date == scenario_date]
            stations = sorted(day_states.station.unique())
            station = st.selectbox("Station", stations, index=stations.index(default.overloaded.station) if default.overloaded.station in stations else 0)
            station_states = day_states[day_states.station == station].sort_values("capacity_utilization", ascending=False)
            source_options = station_states.provider_id.tolist()
            source = st.selectbox("Source DSP", source_options, index=source_options.index(default.overloaded.provider_id) if default.overloaded.provider_id in source_options else 0)
            receiver_options = [value for value in source_options if value != source]
            receiver = st.selectbox("Receiving DSP", receiver_options, index=receiver_options.index(default.receiver.provider_id) if default.receiver.provider_id in receiver_options else 0)
            limit = st.slider("Maximum acceptable utilization", .80, 1.10, .95, .01, format="%.0f%%")
            scenario = simulator.create_scenario(str(scenario_date), station, source, receiver, limit)
            receiver_spare = max(0, int(limit * scenario.receiver.dsp_capacity - scenario.receiver.package_volume))
            if receiver_spare < 1:
                st.warning("The selected receiving DSP has no available capacity under this limit. Choose another DSP or adjust the limit.")
                return
            max_transfer = min(int(scenario.overloaded.package_volume), receiver_spare)
            default_transfer = min(max_transfer, max(1, int(scenario.overloaded.package_volume - limit * scenario.overloaded.dsp_capacity)))
            transfer = st.slider("Volume to reallocate", 1, max_transfer, default_transfer, 1)
            st.markdown(f'<div class="disclaimer"><strong>Available receiving capacity</strong><br>{receiver_spare:,} packages at the selected utilization limit.<br><br><strong>Current source utilization</strong><br>{scenario.overloaded.utilization:.1%}</div>', unsafe_allow_html=True)
            run = st.button("Run Simulation", type="primary", width="stretch")

    with right:
        section_header("Network Impact Preview", "Directional BEFORE → AFTER estimates from synthetic historical relationships.")
        if run or "capacity_result" not in st.session_state:
            try:
                st.session_state.capacity_result = simulator.simulate(scenario, transfer)
            except ValueError as exc:
                st.error(str(exc)); return
        comparison, metadata = st.session_state.capacity_result
        for role, title in [("OVERLOADED_DSP", "Source DSP"), ("RECEIVING_DSP", "Receiving DSP")]:
            subset = comparison[comparison.role == role].set_index("phase")
            _state_panel(title, str(subset.iloc[0].provider_id), subset.loc["BEFORE"], subset.loc["AFTER"])
            st.divider()
        st.markdown("### Recommended Scenario")
        st.info(metadata["recommendation"], icon="↗")
        st.markdown('<div class="disclaimer"><strong>Scenario disclaimer</strong><br>Scenario results are estimates based on historical relationships within synthetic project data and should not be interpreted as production optimization recommendations.</div>', unsafe_allow_html=True)
