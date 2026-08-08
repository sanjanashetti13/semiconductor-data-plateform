QUERIES = {

    "overall_summary": """
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
    """,

    "monthly_yield": """
    SELECT
        YEAR(timestamp) AS production_year,
        MONTH(timestamp) AS production_month,
        COUNT(*) AS total_wafers,
        SUM(CASE WHEN target=-1 THEN 1 ELSE 0 END) AS passed,
        SUM(CASE WHEN target=1 THEN 1 ELSE 0 END) AS failed,
        ROUND(
            SUM(CASE WHEN target=-1 THEN 1 ELSE 0 END) *100.0/
            COUNT(*),
            2
        ) AS yield_percentage
    FROM fact_sensor_readings
    GROUP BY YEAR(timestamp), MONTH(timestamp)
    ORDER BY production_month;
    """,

    "sensor_comparison": """
    SELECT
        AVG(CASE WHEN target=-1 THEN sensor_162 END) AS avg_sensor162_pass,
        AVG(CASE WHEN target=1 THEN sensor_162 END) AS avg_sensor162_fail,
        AVG(CASE WHEN target=-1 THEN sensor_160 END) AS avg_sensor160_pass,
        AVG(CASE WHEN target=1 THEN sensor_160 END) AS avg_sensor160_fail
    FROM fact_sensor_readings;
    """
}