"""Smoke tests for multi-agent planner routing."""

from __future__ import annotations

from ai.agents.base import OrchestratorRequest
from ai.agents.planner_agent import plan
from ai.orchestrator import _optimize_plan
from ai.registry import ensure_registered, list_agents


def test_agents_registered():
    ensure_registered()
    assert set(list_agents()) == {
        "analytics",
        "database",
        "knowledge",
        "ml",
        "powerbi",
        "recommendation",
        "schema",
    }


def test_planner_routes():
    ensure_registered()
    connected = {
        "What is the SECOM dataset?": ["knowledge"],
        "Why did July have the lowest yield and how can we improve it?": [
            "database",
            "recommendation",
        ],
        "Explain every table.": ["schema"],
        "Predict wafer failures.": ["database", "ml"],
        "Open the Power BI dashboard": ["powerbi"],
        "Which month had the lowest yield?": ["database"],
    }
    for question, expected in connected.items():
        req = OrchestratorRequest(question=question, session_id="sess")
        built = _optimize_plan(plan(question, req), req)
        assert [t.agent for t in built.tasks] == expected, question

    req = OrchestratorRequest(question="What is a wafer?")
    built = plan("What is a wafer?", req)
    assert [t.agent for t in built.tasks] == ["knowledge"]
