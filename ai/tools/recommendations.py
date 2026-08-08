"""Manufacturing recommendations tool.

Aggregates overall, monthly, and sensor metrics so the LLM can recommend actions.
"""

from __future__ import annotations

from ai.database import execute_query, format_rows

OVERALL_SQL = """
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

MONTHLY_SQL = """
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
ORDER BY yield_percentage ASC;
"""

SENSOR_SQL = """
SELECT
    AVG(CASE WHEN target = -1 THEN sensor_162 END) AS avg_sensor162_pass,
    AVG(CASE WHEN target = 1 THEN sensor_162 END) AS avg_sensor162_fail,
    AVG(CASE WHEN target = -1 THEN sensor_160 END) AS avg_sensor160_pass,
    AVG(CASE WHEN target = 1 THEN sensor_160 END) AS avg_sensor160_fail
FROM fact_sensor_readings;
"""


def run() -> dict:
    """Gather key manufacturing metrics used for recommendation generation."""
    overall_rows = execute_query(OVERALL_SQL)
    monthly_rows = execute_query(MONTHLY_SQL)
    sensor_rows = execute_query(SENSOR_SQL)

    sections = [
        "=== Overall Summary ===",
        format_rows(
            overall_rows,
            ["total_wafers", "passed", "failed", "yield_percentage"],
        ),
        "",
        "=== Monthly Yield (lowest first) ===",
        format_rows(
            monthly_rows,
            [
                "production_year",
                "production_month",
                "total_wafers",
                "passed",
                "failed",
                "yield_percentage",
            ],
        ),
        "",
        "=== Sensor Comparison ===",
        format_rows(
            sensor_rows,
            [
                "avg_sensor162_pass",
                "avg_sensor162_fail",
                "avg_sensor160_pass",
                "avg_sensor160_fail",
            ],
        ),
    ]

    return {
        "tool": "recommendations",
        "columns": [],
        "rows": overall_rows + monthly_rows + sensor_rows,
        "data": "\n".join(sections),
    }
