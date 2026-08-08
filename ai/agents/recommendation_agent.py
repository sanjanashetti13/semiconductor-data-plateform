"""Recommendation Agent — actionable improvements from analytical findings."""

from __future__ import annotations

import logging
from typing import Any

from ai.agents.base import AgentResult, OrchestratorRequest
from ai.llm import chat
from ai.registry import register

logger = logging.getLogger(__name__)

_SYSTEM = """You are the Recommendation Agent for semiconductor manufacturing.
Given structured findings, propose practical process improvements.
Format:
## Possible Causes
## Recommended Improvements
Keep recommendations tied to the evidence. Do not invent SQL metrics.
"""


@register("recommendation")
def run(goal: str, request: OrchestratorRequest, bag: dict[str, Any]) -> AgentResult:
    """Generate business recommendations from prior findings."""
    question = bag.get("resolved_question") or request.question
    prior = list(bag.get("prior_summaries") or [])

    # Prefer live recommendations tool when no session (Mode 1 warehouse tools)
    if not request.session_id and not prior:
        try:
            from ai.tools import run_tool

            tool_result = run_tool("recommendations", question)
            evidence = tool_result.get("data", "")
            answer = chat(
                [
                    {"role": "system", "content": _SYSTEM},
                    {
                        "role": "user",
                        "content": (
                            f"Goal: {goal}\nQuestion: {question}\n\n"
                            f"Live metrics:\n{evidence}\n\nWrite recommendations."
                        ),
                    },
                ],
                temperature=0.15,
            )
            return AgentResult(
                agent="recommendation",
                success=True,
                summary=answer.strip(),
                data=tool_result,
                meta={
                    "goal": goal,
                    "tool": "recommendations",
                    "data_source": tool_result.get("data_source"),
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Recommendations tool failed: %s", exc)

    if not prior:
        return AgentResult(
            agent="recommendation",
            success=False,
            summary="Need analytical findings before recommending actions.",
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
                        f"Findings:\n" + "\n---\n".join(prior[-4:]) +
                        "\n\nWrite recommendations."
                    ),
                },
            ],
            temperature=0.15,
        )
        return AgentResult(
            agent="recommendation",
            success=True,
            summary=answer.strip(),
            meta={"goal": goal},
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Recommendation agent failed")
        return AgentResult(
            agent="recommendation",
            success=False,
            summary="Could not generate recommendations.",
            error=str(exc),
        )
