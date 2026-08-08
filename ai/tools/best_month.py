"""Best production month tool (highest yield)."""

from __future__ import annotations

from ai.database import execute_query, format_rows

SQL = """
SELECT TOP 1
    production_year,
    production_month,
    total_wafers,
    passed,
    failed,
    yield_percentage
FROM (
    SELECT
        YEAR(timestamp) AS production_year,
        MONTH(timestamp) AS production_month,
        COUNT(*) AS total_wafers,
        SUM(CASE WHEN target = -1 THEN 1 ELSE 0 END) AS passed,
        SUM(CASE WHEN target = 1 THEN 1 ELSE 0 END) AS failed,
        ROUND(
            SUM(CASE WHEN target = -1 THEN 1 ELSE 0 END) * 100.0 /
            COUNT(*),
            2
        ) AS yield_percentage
    FROM fact_sensor_readings
    GROUP BY YEAR(timestamp), MONTH(timestamp)
) monthly
ORDER BY yield_percentage DESC, production_year, production_month;
"""

COLUMNS = [
    "production_year",
    "production_month",
    "total_wafers",
    "passed",
    "failed",
    "yield_percentage",
]


def run() -> dict:
    """Return the production month with the highest yield percentage."""
    rows = execute_query(SQL)
    return {
        "tool": "best_month",
        "columns": COLUMNS,
        "rows": rows,
        "data": format_rows(rows, COLUMNS),
    }
