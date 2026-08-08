"""Dynamic follow-up suggestions grounded in the last answer / profile."""

from __future__ import annotations

from ai.sql_agent.planner import QuestionCategory
from ai.sql_agent.profiler import DatabaseProfile
from ai.sql_agent.semantics import (
    pick_kpi_analytical_view,
    pick_sensor_fact,
    pick_time_dimension,
)


def dynamic_follow_ups(
    *,
    category: QuestionCategory,
    question: str,
    profile: DatabaseProfile | None = None,
    answer: str | None = None,
) -> list[str]:
    """
    Suggest next questions related to the current answer — not static chrome.
    """
    del answer  # reserved for future answer-aware chips
    q = (question or "").lower()
    suggestions: list[str] = []

    view = pick_kpi_analytical_view(profile) if profile else None
    fact = pick_sensor_fact(profile) if profile else None
    dim = pick_time_dimension(profile) if profile else None
    view_name = f"{view.schema}.{view.name}" if view else None
    fact_name = f"{fact.schema}.{fact.name}" if fact else None

    if category == QuestionCategory.KPI:
        if "pass" in q and "fail" not in q:
            suggestions = [
                "How many failed wafers?",
                "What is the overall yield?",
                "What is the total production?",
            ]
        elif "fail" in q:
            suggestions = [
                "How many passed wafers?",
                "What is the overall yield?",
                "Show the production summary",
            ]
        elif "yield" in q:
            suggestions = [
                "How many passed wafers?",
                "How many failed wafers?",
                "Show the production summary",
            ]
        else:
            suggestions = [
                "How many passed wafers?",
                "How many failed wafers?",
                "What is the overall yield?",
            ]
        if fact_name:
            suggestions.append(f"Show sample rows from {fact_name}")
        return suggestions[:4]

    if category == QuestionCategory.KNOWLEDGE:
        return [
            "What is this dataset about?",
            "Explain every table",
            "How many passed wafers?" if view_name or fact_name else "List the tables",
            "Show sample rows" if fact_name else "Show row counts",
        ][:4]

    if category in (
        QuestionCategory.DATABASE_UNDERSTANDING,
        QuestionCategory.SCHEMA,
    ):
        suggestions = ["Explain every table", "Show row counts"]
        if fact_name:
            suggestions.append(f"Show sample rows from {fact_name}")
        if view_name:
            suggestions.append("What is the overall yield?")
        else:
            suggestions.append("Show primary keys")
        return suggestions[:4]

    if category == QuestionCategory.METADATA:
        suggestions = ["What is this dataset about?", "Explain every table"]
        if fact_name:
            suggestions.append(f"Describe {fact_name}")
            suggestions.append(f"Show sample rows from {fact_name}")
        else:
            suggestions.extend(["Show row counts", "Show primary keys"])
        return suggestions[:4]

    # Analytical
    suggestions = []
    if fact_name and ("sensor" in q or "sample" in q):
        suggestions.extend(
            [
                f"Compare average sensor values in {fact_name}",
                f"Show top rows from {fact_name}",
            ]
        )
    if dim and any(k in q for k in ("month", "trend", "year", "daily", "time")):
        suggestions.append("Show a monthly trend for yield")
    if view_name:
        suggestions.append("What is the overall yield?")
    if fact_name:
        suggestions.append(f"Show sample rows from {fact_name}")
    suggestions.extend(
        [
            "What is this dataset about?",
            "Explain every table",
            "Show row counts",
        ]
    )
    # Dedupe preserve order
    seen: set[str] = set()
    unique: list[str] = []
    for s in suggestions:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return unique[:4]
