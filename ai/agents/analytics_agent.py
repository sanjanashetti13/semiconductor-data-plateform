"""Analytics Agent — interpret structured findings (never executes SQL)."""

from __future__ import annotations

import logging
from typing import Any

from ai.agents.base import AgentResult, OrchestratorRequest
from ai.llm import chat
from ai.memory import get_memory
from ai.registry import register

logger = logging.getLogger(__name__)

_SYSTEM = """You are the Analytics Agent for a semiconductor manufacturing copilot.
Interpret the provided structured findings. Never invent numbers not present in the evidence.
Explain trends, yield meaning, and sensor comparisons in business language.
Do not emit SQL. Structure output as:
## Summary
## Analysis
when the question is analytical.
"""


@register("analytics")
def run(goal: str, request: OrchestratorRequest, bag: dict[str, Any]) -> AgentResult:
    """Interpret prior agent / memory evidence without querying the database."""
    question = bag.get("resolved_question") or request.question
    evidence_parts: list[str] = list(bag.get("prior_summaries") or [])

    mem = get_memory(request.session_id)
    if mem and mem.last_sql_result:
        evidence_parts.append(f"Prior SQL result:\n{mem.last_sql_result}")

    if not evidence_parts:
        return AgentResult(
            agent="analytics",
            success=False,
            summary="No analytical evidence available yet.",
            meta={"goal": goal, "skipped": True},
        )

    try:
        answer = chat(
            [
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Goal: {goal}\nQuestion: {question}\n\n"
                        f"Evidence:\n" + "\n---\n".join(evidence_parts[-4:]) +
                        "\n\nWrite the interpretation."
                    ),
                },
            ],
            temperature=0.1,
        )
        return AgentResult(
            agent="analytics",
            success=True,
            summary=answer.strip(),
            meta={"goal": goal},
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Analytics agent failed")
        return AgentResult(
            agent="analytics",
            success=False,
            summary="Analytics interpretation failed.",
            error=str(exc),
        )
