"""Monthly yield breakdown tool."""

from __future__ import annotations

from ai.database import execute_query, format_rows

SQL = """
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
ORDER BY production_year, production_month;
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
    """Query yield metrics grouped by production year and month."""
    rows = execute_query(SQL)
    return {
        "tool": "monthly_yield",
        "columns": COLUMNS,
        "rows": rows,
        "data": format_rows(rows, COLUMNS),
    }
