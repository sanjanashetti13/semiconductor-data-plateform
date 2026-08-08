"""AI router — selects tool + response mode. Never generates SQL."""

from __future__ import annotations

import json
import re
from typing import Any

from ai.llm import chat
from ai.prompt import (
    build_router_system_prompt,
    build_router_user_prompt,
    infer_response_mode,
)
from ai.tools import TOOL_NAMES, tool_catalog

VALID_MODES = {"quick", "standard", "detailed"}


def _extract_json(text: str) -> dict[str, Any]:
    """Parse JSON from a model response, tolerating minor formatting noise."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*?\}", text, flags=re.DOTALL)
        if not match:
            raise ValueError(f"Router did not return JSON: {text}") from None
        return json.loads(match.group(0))


def route(question: str) -> dict[str, str]:
    """
    Use the LLM to choose a tool and response mode.

    Returns:
        {"tool": "<tool_name>", "response_mode": "quick|standard|detailed"}
    """
    system_prompt = build_router_system_prompt(tool_catalog())
    raw = chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": build_router_user_prompt(question)},
        ],
        temperature=0.0,
        json_mode=True,
    )
    payload = _extract_json(raw)
    tool = str(payload.get("tool", "")).strip()

    if tool not in TOOL_NAMES:
        raise ValueError(
            f"Unknown tool selected by router: {tool!r}. "
            f"Expected one of: {sorted(TOOL_NAMES)}"
        )

    mode = str(payload.get("response_mode", "")).strip().lower()
    if mode not in VALID_MODES:
        mode = infer_response_mode(question, tool)
    else:
        # Safety: never let simple knowledge asks become detailed unless explicit.
        if mode == "detailed" and infer_response_mode(question, tool) != "detailed":
            mode = infer_response_mode(question, tool)

    return {"tool": tool, "response_mode": mode}
