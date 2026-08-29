"""Project entry point and lightweight environment smoke check."""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd


def check_environment() -> None:
    """Confirm that the core data stack imports and DuckDB can execute SQL."""
    frame = pd.DataFrame({"synthetic_value": np.array([1, 2, 3])})
    total = duckdb.sql("SELECT SUM(synthetic_value) FROM frame").fetchone()[0]
    if total != 6:
        raise RuntimeError("Environment smoke check returned an unexpected result.")
    print("Environment check passed: core Python data dependencies are working.")


if __name__ == "__main__":
    check_environment()
