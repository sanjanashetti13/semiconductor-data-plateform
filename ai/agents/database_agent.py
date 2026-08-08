"""Database Agent — safe SELECT retrieval via existing SQL / tool layers."""

from __future__ import annotations

import logging
from typing import Any

from ai.agents.base import AgentResult, OrchestratorRequest
from ai.registry import register

logger = logging.getLogger(__name__)


@register("database")
def run(goal: str, request: OrchestratorRequest, bag: dict[str, Any]) -> AgentResult:
    """
    Retrieve structured data. Never invents numbers.

    - With session_id: reuses ``ask_sql_agent`` (validator + executor).
    - Without session: reuses Mode-1 manufacturing tools.
    """
    question = bag.get("resolved_question") or request.question
    tool_hint = bag.get("tool_hint")

    try:
        if request.session_id:
            return _via_sql_agent(request.session_id, question, request.history, goal)
        return _via_manufacturing_tools(question, tool_hint, goal)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Database agent failed")
        return AgentResult(
            agent="database",
            success=False,
            summary="Database retrieval failed.",
            error=str(exc),
        )


def _via_sql_agent(
    session_id: str,
    question: str,
    history: list | None,
    goal: str,
) -> AgentResult:
    from ai.sql_agent.agent import ask_sql_agent

    result = ask_sql_agent(session_id, question, history=history)
    answer = (result.get("answer") or "").strip()
    sql = result.get("sql")
    return AgentResult(
        agent="database",
        success=bool(answer),
        summary=answer or "No data returned.",
        data=result,
        sql=sql if result.get("sql_executed") else None,
        meta={
            "goal": goal,
            "category": result.get("category"),
            "row_count": result.get("row_count", 0),
            "data_source": result.get("data_source"),
            "validation_result": result.get("validation_result"),
            "router_decision": result.get("router_decision"),
            "follow_ups": result.get("follow_ups", []),
            "tool": result.get("tool"),
            "tool_label": result.get("tool_label"),
            "sql_executed": bool(result.get("sql_executed")),
            "visualization": result.get("visualization"),
        },
    )


def _via_manufacturing_tools(
    question: str,
    tool_hint: str | None,
    goal: str,
) -> AgentResult:
    from ai.router import route
    from ai.tools import TOOL_DATA_SOURCES, run_tool

    tool_name = tool_hint
    if not tool_name or tool_name == "knowledge":
        decision = route(question)
        tool_name = decision.get("tool") or "overall_summary"
        if tool_name == "knowledge":
            # Database agent should not answer pure knowledge — signal empty
            return AgentResult(
                agent="database",
                success=False,
                summary="Not a SQL/data question.",
                meta={"goal": goal, "skipped": True},
            )

    tool_result = run_tool(tool_name, question)
    data = tool_result.get("data", "")
    return AgentResult(
        agent="database",
        success=True,
        summary=str(data),
        data=tool_result,
        meta={
            "goal": goal,
            "tool": tool_name,
            "data_source": tool_result.get("data_source")
            or TOOL_DATA_SOURCES.get(tool_name),
            "row_count": len(tool_result.get("rows") or []),
        },
    )
