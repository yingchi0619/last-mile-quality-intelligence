"""Route Risk Intelligence page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app.components.charts import BLUE, ORANGE, RED, style_figure
from app.components.filter_bar import apply_filters, filter_bar
from app.components.kpi_card import kpi_card
from app.components.theme import page_header, section_header
from app.data import feature_importance, model_metrics, risk_scores, selected_risk_model
from app.i18n import local_risk, tr


def _primary_factor(row: pd.Series) -> str:
    signals = {
        "Capacity pressure": row.expected_capacity_utilization / 1.0,
        "Pickup delay": row.pickup_delay_minutes / 20,
        "Low route density": max(0, 1.5 - row.route_density) / .7,
        "Route distance": row.route_distance_miles / 75,
        "Driver reliability": max(0, .98 - row.driver_historical_reliability) / .08,
    }
    factor = max(signals, key=signals.get)
    return tr(factor, {"Capacity pressure": "运力压力", "Pickup delay": "提货延迟", "Low route density": "低路线密度", "Route distance": "路线距离", "Driver reliability": "司机可靠性"}[factor])


def render(routes: pd.DataFrame) -> None:
    scores = risk_scores()
    selected_risk_model()  # Cached artifact readiness check.
    features = routes.rename(columns={"capacity_utilization": "actual_capacity_utilization"}).copy()
    features["expected_capacity_utilization"] = features["planned_packages"] / features["planned_capacity"]
    features["driver_historical_reliability"] = features["driver_reliability"]
    merged = scores.merge(features, on=["route_id", "service_date", "station_id", "provider_id"], how="left", suffixes=("", "_route"))
    page_header(tr("Route Risk Intelligence", "路线风险智能"), tr("Identify potentially high-risk routes before dispatch.", "在发车前识别潜在高风险路线。"), merged["service_date"].max().strftime("%b %d, %Y"))
    current = apply_filters(merged, filter_bar(merged, "risk", 30))
    if current.empty:
        st.info(tr("No scored holdout routes match the selected filters. Risk scores are available only for the chronological holdout period.", "没有符合筛选条件的已评分留出集路线；风险评分仅适用于按时间划分的留出期间。"))
        return
    counts = current.risk_tier.value_counts()
    cols = st.columns(4)
    for col, tier, tone in zip(cols[:3], ["High Risk", "Medium Risk", "Low Risk"], ["red", "orange", "blue"]):
        with col: kpi_card(tr(tier.replace(" Risk", " Risk Routes"), {"High Risk": "高风险路线", "Medium Risk": "中风险路线", "Low Risk": "低风险路线"}[tier]), f"{int(counts.get(tier, 0)):,}", None, tr("selected routes", "所选路线"))
    with cols[3]: kpi_card(tr("Average Risk Score", "平均风险评分"), f"{current.late_delivery_risk_score.mean():.1%}", None, tr("selected routes", "所选路线"))

    section_header(tr("High Risk Route Table", "高风险路线表"), tr("Prioritized route watchlist with the strongest observable operating signal.", "按最强可观察运营信号排序的路线关注清单。"))
    watchlist = current[current["risk_tier"] == "High Risk"].copy()
    watchlist["Primary Risk Factor"] = watchlist.apply(_primary_factor, axis=1)
    watchlist["risk_tier"] = watchlist["risk_tier"].map(local_risk)
    watchlist = watchlist[["route_id", "station_id", "provider_id", "driver_id", "planned_packages", "expected_capacity_utilization", "route_density", "pickup_delay_minutes", "late_delivery_risk_score", "risk_tier", "Primary Risk Factor"]].sort_values("late_delivery_risk_score", ascending=False)
    if watchlist.empty:
        st.info(tr("No high-risk routes match the current filter selection.", "当前筛选条件下没有高风险路线。"))
    else:
        st.dataframe(watchlist, hide_index=True, width="stretch", height=410,
        column_config={"route_id":tr("Route", "路线"), "station_id":tr("Station", "站点"), "provider_id":"DSP", "driver_id":tr("Driver", "司机"),
            "planned_packages":tr("Planned Packages", "计划包裹量"), "expected_capacity_utilization":st.column_config.ProgressColumn(tr("Expected Utilization", "预计利用率"), min_value=0, max_value=1.3, format="%.1%%"),
            "route_density":st.column_config.NumberColumn(tr("Density", "路线密度"), format="%.2f"), "pickup_delay_minutes":st.column_config.NumberColumn(tr("Pickup Delay", "提货延迟"), format="%.1f min"),
            "late_delivery_risk_score":st.column_config.ProgressColumn(tr("Risk Score", "风险评分"), min_value=0, max_value=1, format="%.1%%"), "risk_tier":tr("Risk Level", "风险等级"), "Primary Risk Factor":tr("Primary Risk Factor", "主要风险因素")})

    left, right = st.columns([1.1, .9])
    with left:
        section_header(tr("Risk Distribution", "风险分布"), tr("Holdout route scores segmented by operating risk tier.", "按运营风险等级划分的留出集路线评分。"))
        risk_plot = current.assign(risk_tier_display=current.risk_tier.map(local_risk))
        tier_order = [local_risk(value) for value in ["Low Risk","Medium Risk","High Risk"]]
        fig = px.histogram(risk_plot, x="late_delivery_risk_score", color="risk_tier_display", nbins=30,
            category_orders={"risk_tier_display":tier_order},
            color_discrete_map={tier_order[0]:BLUE,tier_order[1]:ORANGE,tier_order[2]:RED})
        fig.update_xaxes(tickformat=".0%")
        st.plotly_chart(style_figure(fig, 330, True), use_container_width=True, config={"displayModeBar":False})
    with right:
        section_header(tr("Risk Drivers", "风险驱动因素"), tr("Top encoded features from the selected scoring model.", "所选评分模型中影响最大的编码特征。"))
        importance = feature_importance()
        selected = str(current.selected_model.iloc[0])
        top = importance[importance.model == selected].nsmallest(8, "importance_rank").sort_values("absolute_importance")
        top["Feature"] = top.encoded_feature.str.replace("numeric__", "", regex=False).str.replace("categorical__", "", regex=False).str.replace("_", " ")
        if st.session_state.get("language_zh"):
            top["Feature"] = top["Feature"].replace({"expected capacity utilization":"预计运力利用率", "pickup delay minutes":"提货延迟分钟", "route density":"路线密度", "driver historical reliability":"司机历史可靠性", "route distance miles":"路线距离", "planned packages":"计划包裹量", "day of week":"星期"})
        fig = px.bar(top, x="absolute_importance", y="Feature", orientation="h", color_discrete_sequence=[BLUE])
        st.plotly_chart(style_figure(fig, 330), use_container_width=True, config={"displayModeBar":False})

    section_header(tr("Model Performance", "模型表现"), tr("Compact holdout diagnostics; operational prioritization remains the primary use case.", "简要展示留出集诊断指标，核心用途仍是运营优先级排序。"))
    metrics = model_metrics().sort_values("roc_auc", ascending=False)
    cols = st.columns(4)
    best = metrics.iloc[0]
    for col, label, key in zip(cols, ["ROC-AUC", tr("Precision", "精确率"), tr("Recall", "召回率"), "F1"], ["roc_auc", "precision", "recall", "f1_score"]):
        with col: st.metric(label, f"{best[key]:.3f}")
    with st.expander(tr("Model comparison and prototype limitations", "模型对比与原型限制")):
        st.dataframe(metrics, hide_index=True, width="stretch")
        st.caption(tr("Prototype only. Scores are based on synthetic historical relationships and are not production-ready operational decisions.", "仅为原型。评分基于虚构历史关系，不可直接用于生产环境运营决策。"))
