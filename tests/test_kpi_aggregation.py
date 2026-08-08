"""Regression tests: KPI questions must return dataset totals, not first-row grain."""

from __future__ import annotations

from ai.sql_agent.intent import QuestionIntent, classify_intent
from ai.sql_agent.kpi import (
    ViewGrain,
    build_aggregated_kpi_sql,
    build_kpi_sql,
    classify_kpi_metric,
    format_kpi_answer,
    KpiMetric,
    map_kpi_columns,
    parse_kpi_result,
    validate_kpi_totals,
)
from ai.sql_agent.planner import QuestionCategory, classify_question
from ai.sql_agent.profiler import DatabaseProfile, TableProfile
from ai.sql_agent.semantics import enrich_profile_semantics, try_deterministic_kpi_sql


def _periodic_profile() -> DatabaseProfile:
    """
    Simulate vw_manufacturing_summary with multiple daily rows.

    First row alone would wrongly report passed=62.
    Dataset totals: passed=1463, failed=104, total=1567, yield≈93.36%.
    """
    profile = DatabaseProfile(database="semiconductor-db")
    profile.tables = [
        TableProfile(
            "dbo",
            "fact_sensor_readings",
            "TABLE",
            columns=[("reading_id", "int"), ("target", "int")],
            row_count=1567,
        ),
        TableProfile(
            "dbo",
            "dim_time",
            "TABLE",
            columns=[("date_key", "int"), ("month", "int"), ("year", "int")],
        ),
    ]
    profile.views = [
        TableProfile(
            "dbo",
            "vw_manufacturing_summary",
            "VIEW",
            columns=[
                ("production_date", "date"),
                ("total_wafers", "int"),
                ("passed", "int"),
                ("failed", "int"),
                ("yield_percentage", "float"),
            ],
            row_count=25,  # multi-day → must SUM
        ),
    ]
    enrich_profile_semantics(profile)
    return profile


def test_kpi_intent_routing():
    assert classify_intent("How many passed wafers?") == QuestionIntent.KPI
    assert classify_question("How many passed wafers?").category == QuestionCategory.KPI
    assert classify_intent("What is the overall yield?") == QuestionIntent.KPI
    assert classify_intent("What is the total production?") == QuestionIntent.KPI
    assert classify_kpi_metric("How many passed wafers?") == KpiMetric.PASSED
    assert classify_kpi_metric("How many failed wafers?") == KpiMetric.FAILED
    assert classify_kpi_metric("What is the overall yield?") == KpiMetric.YIELD
    assert classify_kpi_metric("What is the total production?") == KpiMetric.TOTAL


def test_kpi_sql_uses_sum_not_top1_for_periodic_view():
    profile = _periodic_profile()
    built = build_kpi_sql(profile, "How many passed wafers?", force_aggregate=False)
    assert built is not None
    sql, source, grain = built
    assert source.name == "vw_manufacturing_summary"
    assert grain == ViewGrain.PERIODIC
    assert "SUM(" in sql.upper()
    assert "TOP" not in sql.upper()
    assert "fact_sensor_readings" not in sql.lower()

    # Legacy helper must also emit SUM SQL
    legacy = try_deterministic_kpi_sql(profile, "How many passed wafers?")
    assert legacy is not None
    assert "SUM(" in legacy.upper()
    assert "TOP" not in legacy.upper()


def test_first_row_bug_is_caught_by_parser_and_validation():
    """
    If SQL wrongly returned grain rows, parser must SUM them —
    never return the first day's passed=62.
    """
    columns = ["total_wafers", "passed", "failed", "yield_percentage"]
    # First row is the buggy day (62); remaining rows make overall totals.
    grain_rows = [
        (100, 62, 38, 62.0),
        (200, 190, 10, 95.0),
        (300, 280, 20, 93.33),
        (400, 380, 20, 95.0),
        (567, 551, 16, 97.18),
    ]
    # 62+190+280+380+551 = 1463; 38+10+20+20+16 = 104; total = 1567
    totals = parse_kpi_result(columns, grain_rows)
    assert totals.passed == 1463
    assert totals.failed == 104
    assert totals.total_wafers == 1567
    assert totals.yield_percentage == 93.36

    # Single first-row result would fail validation against fact size
    bad = parse_kpi_result(columns, [grain_rows[0]])
    ok, reason = validate_kpi_totals(bad, fact_row_count=1567)
    assert ok is False
    assert "suspiciously low" in reason or "!=" in reason or "passed" in reason


def test_aggregated_sql_shape():
    profile = _periodic_profile()
    view = profile.views[0]
    cols = map_kpi_columns(view)
    sql = build_aggregated_kpi_sql(view, cols)
    assert "SUM([passed]) AS passed" in sql
    assert "SUM([failed]) AS failed" in sql
    assert "SUM([total_wafers]) AS total_wafers" in sql
    assert "NULLIF(SUM([total_wafers]), 0)" in sql
    assert "TOP" not in sql.upper()


def test_concise_kpi_answers_match_expected_labels():
    from ai.sql_agent.kpi import KpiTotals

    totals = KpiTotals(
        total_wafers=1567,
        passed=1463,
        failed=104,
        yield_percentage=93.36,
        validated=True,
    )
    assert format_kpi_answer("How many passed wafers?", totals) == "Passed Wafers: 1,463"
    assert format_kpi_answer("How many failed wafers?", totals) == "Failed Wafers: 104"
    assert format_kpi_answer("What is the overall yield?", totals) == "Overall Yield: 93.36%"
    assert (
        format_kpi_answer("What is the total production?", totals)
        == "Total Production: 1,567"
    )


def test_summary_view_skips_sum_when_single_row():
    profile = _periodic_profile()
    profile.views[0].row_count = 1
    built = build_kpi_sql(profile, "How many passed wafers?")
    assert built is not None
    sql, _source, grain = built
    assert grain == ViewGrain.SUMMARY
    assert "SUM(" not in sql.upper()
    assert "TOP" not in sql.upper()
    assert "passed" in sql.lower()
