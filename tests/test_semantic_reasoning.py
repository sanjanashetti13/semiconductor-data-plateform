"""Semantic reasoning / schema knowledge regression tests."""

from __future__ import annotations

from ai.sql_agent.intent import QuestionIntent, classify_intent
from ai.sql_agent.planner import QuestionCategory, classify_question
from ai.sql_agent.profiler import DatabaseProfile, TableProfile
from ai.sql_agent.schema_knowledge import (
    build_schema_knowledge,
    format_full_object_catalog,
)
from ai.sql_agent.semantics import enrich_profile_semantics


def _demo_profile() -> DatabaseProfile:
    profile = DatabaseProfile(database="semiconductor-db")
    profile.tables = [
        TableProfile(
            "dbo",
            "fact_sensor_readings",
            "TABLE",
            columns=[
                ("reading_id", "int"),
                ("target", "int"),
                ("sensor_1", "float"),
                ("timestamp", "datetime"),
            ],
            row_count=1567,
        ),
        TableProfile(
            "dbo",
            "dim_time",
            "TABLE",
            columns=[("date_key", "int"), ("month", "int"), ("year", "int")],
            row_count=365,
        ),
    ]
    profile.views = [
        TableProfile(
            "dbo",
            "vw_manufacturing_summary",
            "VIEW",
            columns=[
                ("total_wafers", "int"),
                ("passed", "int"),
                ("failed", "int"),
                ("yield_percentage", "float"),
            ],
            row_count=25,
        ),
    ]
    enrich_profile_semantics(profile)
    return profile


def test_factual_vs_reasoning_intents():
    assert classify_intent("How many passed?") == QuestionIntent.KPI
    assert classify_intent("Overall yield?") == QuestionIntent.KPI
    assert classify_intent("What is this database used for?") == QuestionIntent.BUSINESS_UNDERSTANDING
    assert classify_intent("Explain this dataset") == QuestionIntent.BUSINESS_UNDERSTANDING
    assert (
        classify_intent("What influences manufacturing yield?")
        == QuestionIntent.BUSINESS_REASONING
    )
    assert (
        classify_intent("How would you reduce failures?")
        == QuestionIntent.BUSINESS_REASONING
    )
    assert classify_intent("What factors influence yield?") == QuestionIntent.BUSINESS_REASONING
    assert classify_intent("Explain every table") == QuestionIntent.SCHEMA
    assert classify_intent("What objects exist?") == QuestionIntent.SCHEMA

    assert (
        classify_question("What influences manufacturing yield?").category
        == QuestionCategory.BUSINESS_REASONING
    )


def test_full_catalog_covers_every_object():
    profile = _demo_profile()
    model = build_schema_knowledge(profile)
    assert model.object_count == 3
    text = format_full_object_catalog(model)
    assert "fact_sensor_readings" in text
    assert "dim_time" in text
    assert "vw_manufacturing_summary" in text
    assert "Purpose" in text
    assert "Typical business usage" in text
    # Must not look like a single-view-only answer
    assert text.lower().count("###") >= 3


def test_knowledge_model_includes_ai_and_domain():
    profile = _demo_profile()
    model = build_schema_knowledge(profile)
    assert "Semiconductor" in model.domain or "manufactur" in model.domain.lower()
    assert model.ai_opportunities
    assert any("sensor" in a.lower() or "fail" in a.lower() for a in model.ai_opportunities)
