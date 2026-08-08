"""Enterprise intent / catalog regression checks."""

from __future__ import annotations

from ai.sql_agent.context import resolve_contextual_question
from ai.sql_agent.intent import QuestionIntent, classify_intent
from ai.sql_agent.planner import QuestionCategory, classify_question
from ai.sql_agent.profiler import DatabaseProfile, TableProfile
from ai.sql_agent.metadata_reasoning import format_explain_tables
from ai.sql_agent.semantics import enrich_profile_semantics


def test_intent_taxonomy():
    assert classify_intent("How many passed wafers?") == QuestionIntent.KPI
    assert classify_intent("What tables exist?") == QuestionIntent.METADATA
    assert classify_intent("Explain every table") == QuestionIntent.SCHEMA
    assert classify_intent("What is this dataset about?") == QuestionIntent.BUSINESS_UNDERSTANDING
    assert classify_intent("Compare sensors") == QuestionIntent.ANALYTICAL
    assert classify_intent("What is the SECOM dataset?") == QuestionIntent.KNOWLEDGE

    assert classify_question("Explain every table.").category == QuestionCategory.SCHEMA
    assert (
        classify_question("What is this dataset about?").category
        == QuestionCategory.BUSINESS_UNDERSTANDING
    )


def test_follow_up_context_resolution():
    history = [
        {"role": "user", "content": "How many passed wafers?"},
        {"role": "assistant", "content": "Passed Wafers: 1,463"},
    ]
    resolved = resolve_contextual_question("and failed?", history)
    assert "failed" in resolved.lower()
    assert "pass" not in resolved.lower() or "failed" in resolved.lower()


def test_explain_tables_includes_purpose_and_usage():
    profile = DatabaseProfile(database="demo")
    profile.tables = [
        TableProfile(
            "dbo",
            "fact_sensor_readings",
            "TABLE",
            columns=[("reading_id", "int"), ("target", "int"), ("sensor_1", "float")],
            row_count=100,
        )
    ]
    profile.views = [
        TableProfile(
            "dbo",
            "vw_manufacturing_summary",
            "VIEW",
            columns=[("passed", "int"), ("failed", "int"), ("yield_percentage", "float")],
            row_count=10,
        )
    ]
    enrich_profile_semantics(profile)
    text = format_explain_tables(profile, include_views=True)
    assert "Purpose" in text
    assert "Main columns" in text
    assert "Usage" in text
    assert "fact_sensor_readings" in text
    assert "vw_manufacturing_summary" in text
