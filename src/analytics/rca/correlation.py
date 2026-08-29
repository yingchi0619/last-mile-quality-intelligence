"""Correlation diagnostics for numeric operational factors."""

from __future__ import annotations

import pandas as pd

from ..kpis import NUMERIC_FACTORS, OUTCOME_METRICS


def correlation_analysis(routes: pd.DataFrame) -> pd.DataFrame:
    """Return Pearson and Spearman relationships for every factor/outcome pair."""
    rows: list[dict[str, object]] = []
    for factor in NUMERIC_FACTORS:
        for outcome in OUTCOME_METRICS:
            pearson = routes[factor].corr(routes[outcome], method="pearson")
            spearman = routes[factor].corr(routes[outcome], method="spearman")
            rows.append(
                {
                    "factor": factor,
                    "outcome": outcome,
                    "pearson_correlation": pearson,
                    "spearman_correlation": spearman,
                    "absolute_pearson_correlation": abs(pearson),
                    "relationship_direction": "POSITIVE" if pearson > 0 else "NEGATIVE",
                }
            )
    result = pd.DataFrame(rows)
    result["influence_rank"] = (
        result.groupby("outcome")["absolute_pearson_correlation"]
        .rank(method="dense", ascending=False)
        .astype(int)
    )
    return result.sort_values(["outcome", "influence_rank", "factor"]).reset_index(drop=True)
