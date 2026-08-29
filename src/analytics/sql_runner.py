"""Read SQL files and return DuckDB results as pandas DataFrames."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Optional, Union

import duckdb
import pandas as pd

from .database import DEFAULT_DATABASE, project_root

PathLike = Union[str, Path]


def read_sql(sql_path: PathLike) -> str:
    """Read a UTF-8 SQL file, resolving relative paths from the project root."""
    path = Path(sql_path)
    if not path.is_absolute():
        path = project_root() / path
    if path.suffix.lower() != ".sql":
        raise ValueError(f"Expected a .sql file, received: {path}")
    return path.read_text(encoding="utf-8")


def execute_query(
    sql: str,
    database_path: Optional[PathLike] = None,
    parameters: Optional[Mapping[str, object]] = None,
) -> pd.DataFrame:
    """Execute SQL against DuckDB and return a detached pandas DataFrame."""
    target = Path(database_path) if database_path else project_root() / DEFAULT_DATABASE
    if not target.is_absolute():
        target = project_root() / target
    with duckdb.connect(str(target), read_only=True) as connection:
        return connection.execute(sql, parameters or {}).fetchdf()


def execute_sql_file(
    sql_path: PathLike,
    database_path: Optional[PathLike] = None,
    parameters: Optional[Mapping[str, object]] = None,
) -> pd.DataFrame:
    """Read and execute a SQL file against the analytical database."""
    return execute_query(read_sql(sql_path), database_path, parameters)
