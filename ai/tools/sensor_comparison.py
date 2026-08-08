"""Sensor 160 vs Sensor 162 comparison tool."""

from __future__ import annotations

from ai.database import execute_query, format_rows

SQL = """
SELECT
    AVG(CASE WHEN target = -1 THEN sensor_162 END) AS avg_sensor162_pass,
    AVG(CASE WHEN target = 1 THEN sensor_162 END) AS avg_sensor162_fail,
    AVG(CASE WHEN target = -1 THEN sensor_160 END) AS avg_sensor160_pass,
    AVG(CASE WHEN target = 1 THEN sensor_160 END) AS avg_sensor160_fail
FROM fact_sensor_readings;
"""

COLUMNS = [
    "avg_sensor162_pass",
    "avg_sensor162_fail",
    "avg_sensor160_pass",
    "avg_sensor160_fail",
]


def run() -> dict:
    """Compare average sensor_160 and sensor_162 values for pass vs fail wafers."""
    rows = execute_query(SQL)
    return {
        "tool": "sensor_comparison",
        "columns": COLUMNS,
        "rows": rows,
        "data": format_rows(rows, COLUMNS),
    }
