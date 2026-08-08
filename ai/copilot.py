"""Copilot orchestrator: question → multi-agent platform → adaptive answer."""

from __future__ import annotations

from ai.orchestrator import run_orchestrator


def ask(question: str) -> str:
    """
    Answer a natural-language manufacturing analytics question.

    Workflow:
        1. Planner Agent builds an execution plan
        2. Specialized agents run (database / knowledge / …)
        3. Orchestrator merges results into the final answer
    """
    return ask_with_metadata(question)["answer"]


def ask_with_metadata(question: str, *, history: list | None = None) -> dict:
    """Run the multi-agent orchestrator and return answer plus metadata."""
    cleaned = question.strip()
    if not cleaned:
        raise ValueError("Question cannot be empty.")

    orch = run_orchestrator(cleaned, history=history or [])
    tool = orch.agents_used[0] if orch.agents_used else orch.tool
    return {
        "tool": tool,
        "response_mode": orch.planner_rationale,
        "data": orch.answer,
        "data_source": orch.data_source,
        "answer": orch.answer,
        "agents_used": orch.agents_used,
        "execution_graph": orch.execution_graph,
        "router_decision": orch.router_decision,
        "validation_result": orch.validation_result,
        "execution_time": orch.execution_time,
    }
