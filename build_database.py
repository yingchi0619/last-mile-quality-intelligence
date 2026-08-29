"""Command-line entry point for building the DuckDB analytics layer."""

from src.analytics import build_database, execute_query


if __name__ == "__main__":
    database_path = build_database()
    inventory = execute_query(
        """
        SELECT table_name AS object_name, 'table' AS object_type
        FROM duckdb_tables() WHERE NOT internal
        UNION ALL
        SELECT view_name, 'view'
        FROM duckdb_views() WHERE NOT internal
        ORDER BY object_type, object_name
        """,
        database_path,
    )
    print(f"DuckDB database built: {database_path}")
    print(inventory.to_string(index=False))
