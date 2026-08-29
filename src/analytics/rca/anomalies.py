"""Rolling z-score anomaly detection for operational KPIs."""

from __future__ import annotations

import numpy as np
import pandas as pd


def zscore_anomaly_detection(rolling: pd.DataFrame, z_threshold: float = 2.0) -> pd.DataFrame:
    """Flag OTD drops and exception spikes against each entity's prior 28 observations."""
    working = rolling.sort_values(["entity_type", "entity_id", "service_date"]).copy()
    grouped = working.groupby(["entity_type", "entity_id"], group_keys=False)
    for metric in ["on_time_delivery_rate", "exception_rate"]:
        prior_mean = grouped[metric].transform(lambda values: values.shift(1).rolling(28, min_periods=14).mean())
        prior_std = grouped[metric].transform(lambda values: values.shift(1).rolling(28, min_periods=14).std())
        working[f"{metric}_prior_28d_mean"] = prior_mean
        working[f"{metric}_zscore"] = (working[metric] - prior_mean) / prior_std.replace(0, np.nan)
    working["anomaly_type"] = np.select(
        [working["on_time_delivery_rate_zscore"] <= -z_threshold, working["exception_rate_zscore"] >= z_threshold],
        ["OTD_DROP", "EXCEPTION_SPIKE"], default="NONE"
    )
    anomalies = working[working["anomaly_type"] != "NONE"].copy()
    anomalies["anomaly_severity"] = np.maximum(
        -anomalies["on_time_delivery_rate_zscore"].fillna(0),
        anomalies["exception_rate_zscore"].fillna(0),
    )
    return anomalies.sort_values("anomaly_severity", ascending=False).reset_index(drop=True)
