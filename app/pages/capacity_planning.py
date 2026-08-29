"""Interactive capacity-planning simulation page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components.kpi_card import kpi_card
from app.components.theme import page_header, section_header
from app.data import capacity_simulator
from app.i18n import tr


def _state_panel(title: str, provider: str, before: pd.Series, after: pd.Series) -> None:
    st.markdown(f"### {title} · `{provider}`")
    cols = st.columns(4)
    metrics = [
        (tr("Utilization", "运力利用率"), "utilization", True, True), (tr("Expected OTD", "预计准时送达率"), "expected_otd", True, False),
        (tr("Packages / Driver", "每名司机包裹数"), "packages_per_driver", False, True), (tr("Exception Risk", "异常风险"), "exception_risk", True, True),
    ]
    for col, (label, key, percent, inverse) in zip(cols, metrics):
        delta = (after[key] - before[key]) * (100 if percent else 1)
        with col: kpi_card(label, f"{after[key]:.1%}" if percent else f"{after[key]:.1f}", delta, tr("after vs before", "调整后较调整前"), inverse, tr("pp", "百分点") if percent else tr("pkg", "件"))
    st.progress(min(float(after["utilization"]), 1.0), text=f"{tr('Capacity load', '运力负载')}：{before['utilization']:.1%} → {after['utilization']:.1%}")


def render(routes: pd.DataFrame) -> None:
    page_header(tr("Capacity Planning Simulator", "运力规划模拟器"), tr("Evaluate package reallocation scenarios before operational execution.", "在运营执行前评估包裹量重新分配场景。"), routes["service_date"].max().strftime("%b %d, %Y"))
    simulator = capacity_simulator()
    default = simulator.select_sample_scenario(.95)
    states = simulator.daily_states
    left, right = st.columns([.34, .66], gap="large")
    with left:
        section_header(tr("Scenario Controls", "场景参数"), tr("Configure a same-day, same-station volume transfer.", "配置同一天、同一站点的包裹量转移。"))
        with st.container(border=True):
            date_options = sorted(states.service_date.dt.date.unique(), reverse=True)
            default_date = pd.Timestamp(default.overloaded.service_date).date()
            scenario_date = st.selectbox(tr("Scenario date", "场景日期"), date_options, index=date_options.index(default_date))
            day_states = states[states.service_date.dt.date == scenario_date]
            stations = sorted(day_states.station.unique())
            station = st.selectbox(tr("Station", "站点"), stations, index=stations.index(default.overloaded.station) if default.overloaded.station in stations else 0)
            station_states = day_states[day_states.station == station].sort_values("capacity_utilization", ascending=False)
            source_options = station_states.provider_id.tolist()
            source = st.selectbox(tr("Source DSP", "转出 DSP"), source_options, index=source_options.index(default.overloaded.provider_id) if default.overloaded.provider_id in source_options else 0)
            receiver_options = [value for value in source_options if value != source]
            receiver = st.selectbox(tr("Receiving DSP", "接收 DSP"), receiver_options, index=receiver_options.index(default.receiver.provider_id) if default.receiver.provider_id in receiver_options else 0)
            limit = st.slider(tr("Maximum acceptable utilization", "最高可接受利用率"), .80, 1.10, .95, .01, format="%.0f%%")
            scenario = simulator.create_scenario(str(scenario_date), station, source, receiver, limit)
            receiver_spare = max(0, int(limit * scenario.receiver.dsp_capacity - scenario.receiver.package_volume))
            if receiver_spare < 1:
                st.warning(tr("The selected receiving DSP has no available capacity under this limit. Choose another DSP or adjust the limit.", "在当前上限下，所选接收 DSP 没有可用运力。请选择其他 DSP 或调整上限。"))
                return
            max_transfer = min(int(scenario.overloaded.package_volume), receiver_spare)
            default_transfer = min(max_transfer, max(1, int(scenario.overloaded.package_volume - limit * scenario.overloaded.dsp_capacity)))
            transfer = st.slider(tr("Volume to reallocate", "重新分配包裹量"), 1, max_transfer, default_transfer, 1)
            st.markdown(f'<div class="disclaimer"><strong>{tr("Available receiving capacity", "接收方可用运力")}</strong><br>{receiver_spare:,} {tr("packages at the selected utilization limit.", "件包裹（按当前利用率上限）。")}<br><br><strong>{tr("Current source utilization", "转出方当前利用率")}</strong><br>{scenario.overloaded.utilization:.1%}</div>', unsafe_allow_html=True)
            run = st.button(tr("Run Simulation", "运行模拟"), type="primary", width="stretch")

    with right:
        section_header(tr("Network Impact Preview", "网络影响预览"), tr("Directional BEFORE → AFTER estimates from synthetic historical relationships.", "基于虚构历史关系的调整前 → 调整后方向性估算。"))
        if run or "capacity_result" not in st.session_state:
            try:
                st.session_state.capacity_result = simulator.simulate(scenario, transfer)
            except ValueError as exc:
                st.error(str(exc)); return
        comparison, metadata = st.session_state.capacity_result
        for role, title in [("OVERLOADED_DSP", tr("Source DSP", "转出 DSP")), ("RECEIVING_DSP", tr("Receiving DSP", "接收 DSP"))]:
            subset = comparison[comparison.role == role].set_index("phase")
            _state_panel(title, str(subset.iloc[0].provider_id), subset.loc["BEFORE"], subset.loc["AFTER"])
            st.divider()
        st.markdown(f"### {tr('Recommended Scenario', '建议场景')}")
        recommendation = metadata["recommendation"]
        if st.session_state.get("language_zh"):
            recommendation = f"该场景建议考虑将 {metadata['transfer_packages']:.0f} 件虚构包裹（占转出方包裹量的 {metadata['transfer_share']:.1%}）从 {scenario.overloaded.provider_id} 转移至 {scenario.receiver.provider_id}（站点 {scenario.overloaded.station}）。此结果仅用于评估方向性影响，执行前仍需验证路线可行性、人员配置与服务约束。"
        st.info(recommendation, icon="↗")
        st.markdown(f'<div class="disclaimer"><strong>{tr("Scenario disclaimer", "场景免责声明")}</strong><br>{tr("Scenario results are estimates based on historical relationships within synthetic project data and should not be interpreted as production optimization recommendations.", "场景结果是基于本项目虚构历史关系的估算，不应被解释为生产环境优化建议。")}</div>', unsafe_allow_html=True)
