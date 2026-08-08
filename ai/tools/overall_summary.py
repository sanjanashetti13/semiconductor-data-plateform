"""Overall production summary tool."""

from __future__ import annotations

from ai.database import execute_query, format_rows

SQL = """
SELECT
    COUNT(*) AS total_wafers,
    SUM(CASE WHEN target = -1 THEN 1 ELSE 0 END) AS passed,
    SUM(CASE WHEN target = 1 THEN 1 ELSE 0 END) AS failed,
    ROUND(
        SUM(CASE WHEN target = -1 THEN 1 ELSE 0 END) * 100.0 /
        COUNT(*),
        2
    ) AS yield_percentage
FROM fact_sensor_readings;
"""

COLUMNS = ["total_wafers", "passed", "failed", "yield_percentage"]


def run() -> dict:
    """Query overall wafer pass/fail counts and yield percentage."""
    rows = execute_query(SQL)
    return {
        "tool": "overall_summary",
        "columns": COLUMNS,
        "rows": rows,
        "data": format_rows(rows, COLUMNS),
    }
