"""Validate SQL views against independently calculated source-table KPIs."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from src.analytics import build_database, execute_query, execute_sql_file


@pytest.fixture(scope="module")
def analytics_database(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_database(tmp_path_factory.mktemp("duckdb") / "test_analytics.duckdb")


def test_route_performance_kpis_match_package_facts(analytics_database: Path) -> None:
    sql_result = execute_query(
        """
        SELECT route_id, on_time_delivery_rate, delivery_success_rate,
               pod_compliance_rate, exception_rate, capacity_utilization,
               pickup_compliance_rate
        FROM route_performance WHERE route_id = 'R000001'
        """,
        analytics_database,
    ).iloc[0]
    with duckdb.connect(str(analytics_database), read_only=True) as connection:
        expected = connection.execute(
            """
            SELECT
                AVG(d.on_time_flag) AS otd,
                AVG(CASE WHEN d.delivery_status = 'DELIVERED' THEN 1.0 ELSE 0.0 END) AS success,
                SUM(d.pod_compliant_flag)::DOUBLE
                    / NULLIF(COUNT(*) FILTER (WHERE d.delivery_status = 'DELIVERED'), 0) AS pod,
                AVG(CASE WHEN d.exception_type <> 'NONE' THEN 1.0 ELSE 0.0 END) AS exceptions,
                r.actual_packages::DOUBLE / r.planned_capacity AS utilization,
                CASE WHEN r.pickup_delay_minutes <= 15 THEN 1.0 ELSE 0.0 END AS pickup_compliance
            FROM deliveries d JOIN routes r USING (route_id)
            WHERE d.route_id = 'R000001'
            GROUP BY r.actual_packages, r.planned_capacity, r.pickup_delay_minutes
            """
        ).fetchone()
    assert sql_result["on_time_delivery_rate"] == pytest.approx(expected[0])
    assert sql_result["delivery_success_rate"] == pytest.approx(expected[1])
    assert sql_result["pod_compliance_rate"] == pytest.approx(expected[2])
    assert sql_result["exception_rate"] == pytest.approx(expected[3])
    assert sql_result["capacity_utilization"] == pytest.approx(expected[4])
    assert sql_result["pickup_compliance_rate"] == pytest.approx(expected[5])


def test_regional_kpis_are_package_weighted(analytics_database: Path) -> None:
    result = execute_query(
        """
        SELECT service_date, on_time_delivery_rate, delivery_success_rate
        FROM daily_regional_performance ORDER BY service_date LIMIT 1
        """,
        analytics_database,
    ).iloc[0]
    expected = execute_query(
        """
        SELECT service_date, AVG(on_time_flag) AS otd,
               AVG(CASE WHEN delivery_status = 'DELIVERED' THEN 1.0 ELSE 0.0 END) AS success
        FROM deliveries GROUP BY service_date ORDER BY service_date LIMIT 1
        """,
        analytics_database,
    ).iloc[0]
    assert result["on_time_delivery_rate"] == pytest.approx(expected["otd"])
    assert result["delivery_success_rate"] == pytest.approx(expected["success"])


def test_all_business_queries_compile_and_execute(analytics_database: Path) -> None:
    query_dir = Path(__file__).resolve().parents[1] / "sql" / "queries"
    for query_file in sorted(query_dir.glob("*.sql")):
        result = execute_sql_file(query_file, analytics_database)
        assert len(result.columns) > 0, f"No result schema returned by {query_file.name}"
