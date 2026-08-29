"""Build and validate the local DuckDB analytical database."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import duckdb

PathLike = Union[str, Path]
DEFAULT_DATABASE = Path("data/processed/last_mile_quality.duckdb")


def project_root() -> Path:
    """Return the repository root independent of the caller's working directory."""
    return Path(__file__).resolve().parents[2]


def _loader_sql(root: Path) -> str:
    sql = (root / "sql" / "00_load_tables.sql").read_text(encoding="utf-8")
    raw_prefix = (root / "data" / "raw").as_posix().replace("'", "''") + "/"
    return sql.replace("data/raw/", raw_prefix)


def build_database(database_path: Optional[PathLike] = None) -> Path:
    """Materialize raw tables and create all analytical views."""
    root = project_root()
    target = Path(database_path) if database_path else root / DEFAULT_DATABASE
    if not target.is_absolute():
        target = root / target
    target.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(target)) as connection:
        connection.execute(_loader_sql(root))
        for sql_file in sorted((root / "sql" / "views").glob("*.sql")):
            connection.execute(sql_file.read_text(encoding="utf-8"))

        expected_views = {
            "route_performance",
            "dsp_performance",
            "station_performance",
            "daily_regional_performance",
            "driver_performance",
            "exception_analysis",
        }
        actual_views = {
            row[0]
            for row in connection.execute(
                "SELECT view_name FROM duckdb_views() WHERE NOT internal"
            ).fetchall()
        }
        missing = expected_views - actual_views
        if missing:
            raise RuntimeError(f"Database build is missing views: {sorted(missing)}")
    return target
