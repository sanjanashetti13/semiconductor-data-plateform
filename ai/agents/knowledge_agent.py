"""Knowledge Agent — curated domain answers without SQL."""

from __future__ import annotations

import logging
from typing import Any

from ai.agents.base import AgentResult, OrchestratorRequest
from ai.llm import chat
from ai.registry import register

logger = logging.getLogger(__name__)

_SYSTEM = """You are the Knowledge Agent for Semiconductor Intelligence Hub.
Answer using ONLY the provided knowledge base and prior agent notes.
Be clear and concise. Do not invent live SQL metrics or row counts.
If the question is a greeting, reply briefly and offer analytics help.
"""


@register("knowledge")
def run(goal: str, request: OrchestratorRequest, bag: dict[str, Any]) -> AgentResult:
    """Answer conceptual questions from the curated knowledge base."""
    question = bag.get("resolved_question") or request.question
    prior = bag.get("prior_summaries") or []

    try:
        from ai.tools.knowledge import run as knowledge_run

        kb = knowledge_run(question)
        evidence = kb.get("data", "")
        if prior:
            evidence = evidence + "\n\nPrior agent notes:\n" + "\n---\n".join(prior[-3:])

        answer = chat(
            [
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Goal: {goal}\n\nQuestion: {question}\n\n"
                        f"Knowledge base:\n{evidence}\n\n"
                        "Write the user-facing answer."
                    ),
                },
            ],
            temperature=0.15,
        )
        return AgentResult(
            agent="knowledge",
            success=True,
            summary=answer.strip(),
            data=kb,
            meta={"goal": goal, "data_source": "Project Knowledge Base"},
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Knowledge agent failed")
        return AgentResult(
            agent="knowledge",
            success=False,
            summary="Knowledge lookup failed.",
            error=str(exc),
        )
