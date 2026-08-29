"""Exception Pareto analysis."""

import pandas as pd


def exception_pareto_analysis(exception_facts: pd.DataFrame) -> pd.DataFrame:
    counts = exception_facts.groupby("exception_type").size().rename("exception_packages").sort_values(ascending=False).reset_index()
    counts["exception_share"] = counts["exception_packages"] / counts["exception_packages"].sum()
    counts["cumulative_exception_share"] = counts["exception_share"].cumsum()
    counts["pareto_rank"] = range(1, len(counts) + 1)
    counts["within_80_percent_pareto"] = (counts["cumulative_exception_share"].shift(fill_value=0) < 0.80).astype(int)
    return counts
