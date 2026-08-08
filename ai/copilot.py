"""Copilot orchestrator: question → router → tool → adaptive answer."""

from __future__ import annotations

from ai.llm import chat
from ai.prompt import (
    ADAPTIVE_RESPONSE_SYSTEM_PROMPT,
    build_adaptive_user_prompt,
    infer_response_mode,
)
from ai.router import route
from ai.tools import TOOL_DATA_SOURCES, run_tool


def ask(question: str) -> str:
    """
    Answer a natural-language manufacturing analytics question.

    Workflow:
        1. Router selects tool + response mode
        2. Tool gathers evidence (SQL or knowledge)
        3. LLM answers with adaptive sizing (quick / standard / detailed)
    """
    return ask_with_metadata(question)["answer"]


def ask_with_metadata(question: str) -> dict:
    """Route, execute tool, and return answer plus execution metadata."""
    cleaned = question.strip()
    if not cleaned:
        raise ValueError("Question cannot be empty.")

    decision = route(cleaned)
    tool_name = decision["tool"]
    response_mode = decision.get("response_mode") or infer_response_mode(
        cleaned,
        tool_name,
    )

    tool_result = run_tool(tool_name, cleaned)
    data = tool_result["data"]
    data_source = tool_result.get("data_source") or TOOL_DATA_SOURCES.get(
        tool_name,
        "Unknown",
    )

    answer = chat(
        [
            {"role": "system", "content": ADAPTIVE_RESPONSE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_adaptive_user_prompt(
                    cleaned,
                    data,
                    source=data_source,
                    response_mode=response_mode,
                ),
            },
        ],
        temperature=0.1,
    )

    return {
        "tool": tool_name,
        "response_mode": response_mode,
        "data": data,
        "data_source": data_source,
        "answer": answer,
    }
