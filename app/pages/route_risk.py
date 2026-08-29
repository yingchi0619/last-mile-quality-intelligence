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


def _primary_factor(row: pd.Series) -> str:
    signals = {
        "Capacity pressure": row.expected_capacity_utilization / 1.0,
        "Pickup delay": row.pickup_delay_minutes / 20,
        "Low route density": max(0, 1.5 - row.route_density) / .7,
        "Route distance": row.route_distance_miles / 75,
        "Driver reliability": max(0, .98 - row.driver_historical_reliability) / .08,
    }
    return max(signals, key=signals.get)


def render(routes: pd.DataFrame) -> None:
    scores = risk_scores()
    selected_risk_model()  # Cached artifact readiness check.
    features = routes.rename(columns={"capacity_utilization": "actual_capacity_utilization"}).copy()
    features["expected_capacity_utilization"] = features["planned_packages"] / features["planned_capacity"]
    features["driver_historical_reliability"] = features["driver_reliability"]
    merged = scores.merge(features, on=["route_id", "service_date", "station_id", "provider_id"], how="left", suffixes=("", "_route"))
    page_header("Route Risk Intelligence", "Identify potentially high-risk routes before dispatch.", merged["service_date"].max().strftime("%b %d, %Y"))
    current = apply_filters(merged, filter_bar(merged, "risk", 30))
    if current.empty:
        st.info("No scored holdout routes match the selected filters. Risk scores are available only for the chronological holdout period.")
        return
    counts = current.risk_tier.value_counts()
    cols = st.columns(4)
    for col, tier, tone in zip(cols[:3], ["High Risk", "Medium Risk", "Low Risk"], ["red", "orange", "blue"]):
        with col: kpi_card(tier.replace(" Risk", " Risk Routes"), f"{int(counts.get(tier, 0)):,}", None, "selected routes")
    with cols[3]: kpi_card("Average Risk Score", f"{current.late_delivery_risk_score.mean():.1%}", None, "selected routes")

    section_header("High Risk Route Table", "Prioritized route watchlist with the strongest observable operating signal.")
    watchlist = current[current["risk_tier"] == "High Risk"].copy()
    watchlist["Primary Risk Factor"] = watchlist.apply(_primary_factor, axis=1)
    watchlist = watchlist[["route_id", "station_id", "provider_id", "driver_id", "planned_packages", "expected_capacity_utilization", "route_density", "pickup_delay_minutes", "late_delivery_risk_score", "risk_tier", "Primary Risk Factor"]].sort_values("late_delivery_risk_score", ascending=False)
    if watchlist.empty:
        st.info("No high-risk routes match the current filter selection.")
    else:
        st.dataframe(watchlist, hide_index=True, width="stretch", height=410,
        column_config={"route_id":"Route", "station_id":"Station", "provider_id":"DSP", "driver_id":"Driver",
            "planned_packages":"Planned Packages", "expected_capacity_utilization":st.column_config.ProgressColumn("Expected Utilization", min_value=0, max_value=1.3, format="%.1%%"),
            "route_density":st.column_config.NumberColumn("Density", format="%.2f"), "pickup_delay_minutes":st.column_config.NumberColumn("Pickup Delay", format="%.1f min"),
            "late_delivery_risk_score":st.column_config.ProgressColumn("Risk Score", min_value=0, max_value=1, format="%.1%%"), "risk_tier":"Risk Level"})

    left, right = st.columns([1.1, .9])
    with left:
        section_header("Risk Distribution", "Holdout route scores segmented by operating risk tier.")
        fig = px.histogram(current, x="late_delivery_risk_score", color="risk_tier", nbins=30,
            category_orders={"risk_tier":["Low Risk","Medium Risk","High Risk"]},
            color_discrete_map={"Low Risk":BLUE,"Medium Risk":ORANGE,"High Risk":RED})
        fig.update_xaxes(tickformat=".0%")
        st.plotly_chart(style_figure(fig, 330, True), width="stretch", config={"displayModeBar":False})
    with right:
        section_header("Risk Drivers", "Top encoded features from the selected scoring model.")
        importance = feature_importance()
        selected = str(current.selected_model.iloc[0])
        top = importance[importance.model == selected].nsmallest(8, "importance_rank").sort_values("absolute_importance")
        top["Feature"] = top.encoded_feature.str.replace("numeric__", "", regex=False).str.replace("categorical__", "", regex=False).str.replace("_", " ")
        fig = px.bar(top, x="absolute_importance", y="Feature", orientation="h", color_discrete_sequence=[BLUE])
        st.plotly_chart(style_figure(fig, 330), width="stretch", config={"displayModeBar":False})

    section_header("Model Performance", "Compact holdout diagnostics; operational prioritization remains the primary use case.")
    metrics = model_metrics().sort_values("roc_auc", ascending=False)
    cols = st.columns(4)
    best = metrics.iloc[0]
    for col, label, key in zip(cols, ["ROC-AUC", "Precision", "Recall", "F1 Score"], ["roc_auc", "precision", "recall", "f1_score"]):
        with col: st.metric(label, f"{best[key]:.3f}")
    with st.expander("Model comparison and prototype limitations"):
        st.dataframe(metrics, hide_index=True, width="stretch")
        st.caption("Prototype only. Scores are based on synthetic historical relationships and are not production-ready operational decisions.")
