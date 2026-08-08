"""Tests for sensor vs KPI routing and visualization helpers."""

from __future__ import annotations

from ai.sql_agent.intent import is_factual_kpi_question
from ai.sql_agent.kpi import is_kpi_route, is_sensor_analytics_question
from ai.sql_agent.visualization import build_visualization, wants_visualization


def test_sensor_avg_is_not_kpi_route():
    q = "What are the average values of sensor_000 through sensor_007?"
    assert is_sensor_analytics_question(q)
    assert not is_kpi_route(q)
    assert not is_factual_kpi_question(q)


def test_passed_wafers_still_kpi():
    q = "How many passed wafers?"
    assert is_kpi_route(q)
    assert is_factual_kpi_question(q)


def test_highest_sensor_average_not_kpi():
    q = "Which sensor has the highest average value?"
    assert is_sensor_analytics_question(q)
    assert not is_kpi_route(q)


def test_visualization_from_wide_row():
    viz = build_visualization(
        "Show average sensor values",
        ["sensor_000", "sensor_001", "sensor_002"],
        [(3014.44, 2495.87, 2200.55)],
    )
    assert viz is not None
    assert viz["type"] == "bar"
    assert len(viz["data"]) == 3


def test_no_viz_for_simple_yield():
    assert not wants_visualization(
        "What is the average yield?",
        row_count=1,
        column_count=1,
    )
